from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np


CONFIG_PATH = Path(__file__).resolve().parent / "config.json"
DATA_DIR = Path(__file__).resolve().parent / "data"
buffer = 100  # Buffer for agent IDs to avoid collisions with initial agents

class Agent:
    def __init__(self, agent_id: int, behavior: str, resources: float, decay: float, death_timer: float, age: int):
        self.id = agent_id
        self.behavior = behavior
        self.resources = resources
        self.memory: Dict[int, Dict[str, float]] = {}
        self.proSocial = 0.0
        self.decay = decay # in per one [0, 1], how much is remembered per tick, the bigger, the more is remembered.
        self.death_timer = death_timer
        self.age = age

    def decay_memory(self) -> None:
        for actor_id in list(self.memory):
            entry = self.memory[actor_id]
            for key in list(entry):
                entry[key] *= self.decay
            if all(value < 1e-6 for value in entry.values()):
                del self.memory[actor_id]

    def remember(self, actor_id: int, action: str, amount: float) -> None:
        if actor_id not in self.memory:
            self.memory[actor_id] = {"share": 0.0, "hoard": 0.0, "defect": 0.0}
        self.memory[actor_id][action] += max(1+amount, 0.0)# added one to remember the behaviour independently on the absolute value
    
        ##print(f"Agent {self.id} remembers Agent {actor_id} action '{action}' with amount {amount:.3f}. Total memory: {self.memory[actor_id][action]:.3f}")

    def alive(self) -> bool:
        if self.age > random.normalvariate(4, 0.5):  # Example age threshold for death
            prob_death = 1.0 - math.exp(-self.age / 100.0)  # Example age-based death probability
        else:
            prob_death = 0.1
        return self.resources >= 0 and self.death_timer > 0 and random.random() > prob_death
    
    def maybe_switch_behavior(self, prob_beh: float, rng: random.Random) -> None:
        if rng.random() < prob_beh:
            choices = ["share", "hoard", "defect"]
            weights = [1.0, 1.0, 1.0]
            current_idx = choices.index(self.behavior)
            weights[current_idx] += 2.0
            self.behavior = weighted_choice(choices, weights, rng)

    def to_dict(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "behavior": self.behavior,
            "resources": round(self.resources, 3),
            "death_timer": round(self.death_timer, 3),
            "memory": {
                str(actor_id): {action: round(value, 3) for action, value in values.items()}
                for actor_id, values in self.memory.items()
            },
        }


def weighted_choice(options: List[str], weights: List[float], rng: random.Random) -> str:
    '''
    returns a random choice from options based on the provided weights.

    works by generating a random number between 0 and the sum of the weights,
    and then iterating through the options, summing their weights until the 
    sum exceeds the random number.
    The option at that point is returned.
    if all weights are zero, the first option is returned.
    '''
    
    total = sum(weights)
    if total <= 0:
        return options[0]
    threshold = rng.random() * total
    running = 0.0
    for option, weight in zip(options, weights):
        running += weight
        if running >= threshold:
            return option
    return options[-1]


def load_config(path: Path) -> Dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def init_agents(config: Dict[str, object], rng: random.Random) -> List[Agent]:
    n = int(config["N"])
    needed = float(config["Needed"])
    decay = float(config["Decay"])
    base_death_timer = float(config["BaseDeathTimer"])
    weight_ini_share = float(config["weightIniShare"])
    weight_ini_hoard = float(config["weightIniHoard"])
    weight_ini_defect = float(config["weightIniDefect"])

    agents: List[Agent] = []
    for index in range(n):
        behavior = weighted_choice(
            ["share", "hoard", "defect"], [weight_ini_share, weight_ini_hoard, weight_ini_defect], rng
        )
        agents.append(
            Agent(
                agent_id=index,
                behavior=behavior,
                resources=needed,
                decay=decay,
                death_timer=rng.uniform(1, base_death_timer),
                age=rng.lognormvariate(np.log(20), np.log(40.5)),  # Log-normal distribution for age
            )
        )
    return agents


def distribute_resources(total_resources: float, agents: List[Agent], needed: float, max_storage: float, rng: random.Random) -> List[Agent]:
    n_agents = len(agents)
    if n_agents <= 0:
        return []
    if total_resources <= 0:
        return [0.0 for _ in range(n_agents)]
    
    used = 0.0
    for agent in agents:
        if agent.resources > max_storage:
            agent.resources = max_storage  # Cap resources to avoid excessive accumulation
        if agent.age < rng.normalvariate(7, 0.5): # or agent.age > rng.normalvariate(85, 3):
            agent.resources = 2
            used += needed  # Agent is too young or too old, gets only the needed resources
            #print(f"Agent {agent.id} (age: {agent.age:.2f}), ", rng.normalvariate(7, 0.5))
    remaining_resources = max(0.0, total_resources - used)
    
    weights = [rng.random() for _ in range(n_agents-int(used/needed))]
    #weights = [abs(rng.normalvariate(1,0.2)) for _ in range(n_agents-int(used/needed))]
    total_weight = sum(weights)
    for agent in agents:
        if agent.age > rng.normalvariate(7, 0.5): #and agent.age < rng.normalvariate(85, 3):
            receive = (remaining_resources * weights.pop() / total_weight if weights else 0.0)
            agent.resources += receive - needed
    return agents

def advance_environment(current_environment: str, chang: float, reNeutral: float, rng: random.Random) -> str:
    if current_environment == "neutral":
        if rng.random() < chang:
            return rng.choice(["abundant", "scarce"])
        return "neutral"
    if rng.random() < reNeutral:
        return "neutral"
    return current_environment


def produce_environment_resources(environment: str, needed: float, N: int, rng: random.Random) -> float:
    if environment == "abundant":
        return rng.uniform(2.0 * needed * N, 10.0 * needed * N)
    if environment == "scarce":
        return rng.uniform(0.1 * needed * N, 0.5 * needed * N)
    return needed * N + 2


def choose_target(agent: Agent, others: List[Agent], rng: random.Random) -> Optional[Agent]:
    '''
    Chooses a target agent for sharing based on the agent's memory of others' behaviors.'
    if there are no eligible targets, returns None.
    implements a weighted choice based on the agent's memory of others' sharing and hoarding behaviors.
    input: agent - the agent making the choice
           others - the list of other agents to choose from
           rng - a random number generator for reproducibility
    output: the chosen target agent or None if no eligible targets exist
    '''
    #if agent.age < rng.normalvariate(16, 3):# or agent.age > rng.normalvariate(65, 3):
    #    return agent # Agent is too young or too old, so is always chosen     
    
    eligible = [other for other in others if other.id != agent.id ]
    eligible = [other for other in eligible if other.behavior != "defect" ]

    if not eligible:
        return None

    sharers: List[float] = [] 
    hoarders: List[float] = [] 
    for other in eligible:
    
        if other.proSocial > random.uniform(0.0, 1.0):
            print(f"Who {agent.id}, remembers {other.id}: proSocial={other.proSocial:.3f} and shares.")
            sharers.append(other.id)
        
        if other.proSocial < 0.0:
            hoarders.append(other.id)
        
    if len(sharers) > 0:
        chosen_id = random.choice(sharers)
    else:
        chosen_id = random.choice(list(set(eligible) - set(hoarders))) 
    for other in eligible:
        if other.id == chosen_id:
            print(f"ID {agent.id} is {agent.behavior} chose {other.id} with memory share={agent.memory.get(other.id, {}).get('share', 0.0):.3f}")
            return other
    return None


def should_reproduce(agent: Agent, needed: float, MaxChilds: float, re_rate: float, rng: random.Random) -> bool:

    if agent.age < rng.normalvariate(16, 3) or agent.age > rng.normalvariate(45, 3):
        return False
    else:   
        sigma = max(0.1, min(1.5, np.log(agent.resources / max(needed, 1e-6))))
        sample = rng.lognormvariate(mu=re_rate, sigma=sigma)
        return sample > 1.5


def simulate(config: Dict[str, object], verbose: bool = False) -> Dict[str, object]:
    rng = random.Random(int(config["seed"]))
    agents = init_agents(config, rng)
    ticks = int(config["ticks"])
    needed = float(config["Needed"])
    re_rate = float(config["ReRate"])
    max_childs = float(config["MaxChilds"])
    decay = float(config["Decay"])
    prob_beh = float(config["probBeh"])
    chang = float(config["Chang"])
    reNeutral = float(config["ReNeutral"])
    share_fraction = float(config.get("ShareFraction", 0.35))
    base_death_timer = float(config.get("BaseDeathTimer", 3.0))
    max_storage = float(config["MaxStorage"])
    N = int(config["N"])

    history: List[Dict[str, object]] = []
    environment = "neutral"

    for tick in range(ticks):
        environment = advance_environment(environment, chang, reNeutral, rng)
        env_resources = produce_environment_resources(environment, needed, N, rng)

        agents = distribute_resources(env_resources, agents, needed, max_storage, rng)
        #for agent, allocation in zip(agents, allocations):
        #    agent.resources += allocation - needed
        
        for agent in agents:
            agent.decay_memory()
            agent.maybe_switch_behavior(prob_beh, rng)
            agent.age += 1

        next_generation: List[Agent] = []
        total_reproductions = 0
        total_deaths = 0

        for agent in agents:
            if agent.resources < 0:
                continue  # Skip agents with negative resources

            if agent.resources >= needed and agent.behavior == "share":
                target = choose_target(agent, agents, rng)
                if target is not None:
                    share_amount = min(agent.resources - needed, share_fraction * max(1.0, agent.resources / max(needed, 1e-6)))
                    if share_amount > 0.0 and agent.resources >= share_amount:
                        agent.resources -= share_amount
                        target.resources += share_amount
                        agent.proSocial = (agent.proSocial + share_amount/(agent.resources - needed))

            if agent.behavior == "hoard":
                # Hoarders recieve and keep their resources and do not share
                agent.proSocial = (agent.proSocial - (agent.resources - needed))
        
            # Defectors keep their resources but do not recieve nor share

            if  agent.resources > needed and should_reproduce(agent, needed, max_childs, re_rate, rng):
                
                sigma = max(0.1, min(1.5, agent.resources / max(needed, 1e-6)))
                reproduction_chance = int(abs(rng.normalvariate(mu=max_childs, sigma=sigma))+0.5)
                available_resources = agent.resources - needed*(reproduction_chance+1)
                reproduction_events = max(int(available_resources / needed), int((agent.resources - needed)/needed) )
               
                for _ in range(reproduction_events):
                    total_reproductions += reproduction_events
                    child_behavior = agent.behavior
                    #if rng.random() < prob_beh:
                    #    child_behavior = weighted_choice(["share", "hoard", "defect"], [1.0, 1.0, 1.0], rng)
                    child = Agent(
                        agent_id=buffer + len(agents) + len(next_generation),
                        behavior=child_behavior,
                        resources=0.0,
                        decay=decay,
                        death_timer=rng.uniform(1, float(config["BaseDeathTimer"])),
                        age=0
                    )
                    next_generation.append(child)

            still_alive = agent.alive()
            if agent.resources >= needed and still_alive:
                agent.death_timer = rng.uniform(agent.death_timer, base_death_timer)
                agent.resources = 1#needed#min(needed, agent.resources)
                next_generation.append(agent)
            else:
                agent.death_timer -= 1.0
                if agent.death_timer >= 0.0 and still_alive:
                    agent.resources = 1
                    next_generation.append(agent)
                    
                else:
                    total_deaths += 1
         
            
        agents = next_generation
        history.append(
            {
                "tick": tick,
                "environment": environment,
                "resources_produced": round(env_resources, 3),
                "population": len(agents),
                "behavior_counts": {behavior: sum(1 for agent in agents if agent.behavior == behavior) for behavior in ["share", "hoard", "defect"]},
                "agents": [agent.to_dict() for agent in agents],
            }
        )
        #if verbose and tick % 10 == 0:
        #    print(f"Tick {tick}: Environment={environment}, Resources={env_resources:.2f}, Population={len(agents)}")
        #    print(f"total reproductions: {total_reproductions}, total deaths: {total_deaths}")
        

    return {"config": config, "history": history}


def write_output(data: Dict[str, object], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "simulation_results.json").open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)


def main() -> None:
    config = load_config(CONFIG_PATH)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    results = simulate(config, verbose=True)
    write_output(results, DATA_DIR)
    print(f"Simulation complete. Wrote {DATA_DIR / 'simulation_results.json'}")


if __name__ == "__main__":
    main()
