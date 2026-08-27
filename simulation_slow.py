from __future__ import annotations

import json
import math
import random
from random import Random as rand
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np


CONFIG_PATH = Path(__file__).resolve().parent / "config.json"
DATA_DIR = Path(__file__).resolve().parent / "data"
buffer = 10  # Buffer for agent IDs to avoid collisions with initial agents

class Agent:
    def __init__(self, agent_id: int, behavior: str, resources: float, decay: float, repAge: float, menoAge: float, death_timer: float, age: int):
        self.id = agent_id
        self.behavior = behavior
        self.resources = resources
        self.proSocial = 0.0
        self.decay = decay # in per one [0, 1], how much is remembered per tick, the bigger, the more is remembered.
        self.repAge = repAge
        self.menoAge = menoAge
        self.death_timer = death_timer
        self.age = age
    
    def alive(self) -> bool:
        if self.age > random.normalvariate(4, 0.5):  # Example age threshold for death
            prob_death = 1.0 - math.exp(-self.age / 100.0)  # Example age-based death probability
        else:
            prob_death = 0.1
        return self.resources >= 0 and self.death_timer > 0 and random.random() > prob_death
    
    def maybe_switch_behavior(self, prob_beh: float) -> None:
        if random.random() < prob_beh:
            choices = ["share", "hoard"]
            weights = [1.0, 1.0]
            current_idx = choices.index(self.behavior)
            weights[current_idx] += 2.0
            self.behavior = weighted_choice(choices, weights)

    def to_dict(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "behavior": self.behavior,
            "resources": round(self.resources, 3),
            "death_timer": round(self.death_timer, 3),
            "proSocial": round(self.proSocial, 3)
        }


def weighted_choice(options: List[str], weights: List[float]) -> str:
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
    threshold = random.random() * total
    running = 0.0
    for option, weight in zip(options, weights):
        running += weight
        if running >= threshold:
            return option
    return options[-1]


def load_config(path: Path) -> Dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sample_hunter_gatherer_age() -> int:
    '''
    simulator sampling from six weighted age bands,
    40% of the initial population under 15, 4% aged 65–80. 
    '''
    age_bands = [(0, 4), (5, 14), (15, 24), (25, 44), (45, 64), (65, 80)]
    band_weights = [0.18, 0.22, 0.16, 0.25, 0.15, 0.04]
    band_start, band_end = random.choices(age_bands, weights=band_weights, k=1)[0]
    return random.randint(band_start, band_end)


def init_agents(config: Dict[str, object]) -> List[Agent]:
    n = int(config["N"])
    needed = float(config["Needed"])
    decay = float(config["Decay"])
    base_death_timer = float(config["BaseDeathTimer"])
    weight_ini_share = float(config["weightIniShare"])
    weight_ini_hoard = float(config["weightIniHoard"])
    rep_age = float(config.get("ReproductiveAge", 16))
    var_rep_age = float(config.get("varReproductiveAge", 3))
    meno_age = float(config.get("MenopausalAge", 45))
    var_meno_age = float(config.get("varMenopausalAge", 3))

    agents: List[Agent] = []
    for index in range(n):
        behavior = weighted_choice(
            ["share", "hoard"], [weight_ini_share, weight_ini_hoard]
        )
        agents.append(
            Agent(
                agent_id=index,
                behavior=behavior,
                resources=needed,
                decay=decay,
                repAge = random.normalvariate(rep_age, var_rep_age),
                menoAge = random.normalvariate(meno_age, var_meno_age),
                death_timer=random.uniform(1, base_death_timer),
                age=sample_hunter_gatherer_age(),
            
            )
        )
    return agents


def distribute_resources(total_resources: float, agents: List[Agent], needed: float, max_storage: float) -> List[Agent]:
    n_agents = len(agents)
    if n_agents <= 0:
        return []
    if total_resources <= 0:
        return [0.0 for _ in range(n_agents)]
    
    used = 0.0
    for agent in agents:
        if agent.resources > max_storage:
            agent.resources = max_storage  # Cap resources to avoid excessive accumulation
        if agent.age < agent.repAge/2 : 
            agent.resources = 2
            used += needed  # Agent is too young, gets only the needed resources
  
    remaining_resources = max(0.0, total_resources - used)
    
    weights = [random.random() for _ in range(n_agents-int(used/needed))]
    
    total_weight = sum(weights)
    for agent in agents:
        #distribute resources to the not too young, not too old agents
        if agent.age > agent.repAge/2 and agent.age < agent.menoAge*2: 
            receive = (remaining_resources * weights.pop() / total_weight if weights else 0.0)
            agent.resources += receive - needed
    return agents

def advance_environment(current_environment: str, chang: float, reNeutral: float) -> str:
    if current_environment == "neutral":
        if random.random() < chang:
            return random.choice(["abundant", "scarce"])
        return "neutral"
    if random.random() < reNeutral:
        return "neutral"
    return current_environment


def produce_environment_resources(environment: str, needed: float, N: int) -> float:
    if environment == "abundant":
        return random.uniform(2.0 * needed * N, 10.0 * needed * N)
    if environment == "scarce":
        return random.uniform(0.1 * needed * N, 0.5 * needed * N)
    return needed * N + 2


def choose_target(agent: Agent, others: List[Agent], share_th: float) -> Optional[Agent]:
    '''
    Chooses a target agent for sharing based on the agent's memory proSOciality.'
    if there are no eligible targets, returns None.
    implements a weighted choice based on the agent's averaged proSOciality of others' sharing and hoarding behaviors.
    input: agent - the agent making the choice
           others - the list of other agents to choose from
    output: the chosen target agent or None if no eligible targets exist
    '''

    eligible = [other for other in others if other.id != agent.id]

    if not eligible:
        return None

    sharers: List[Agent] = []
    hoarders: List[Agent] = []
    for other in eligible:
        if other.proSocial > random.uniform(0.0, share_th):
            sharers.append(other)

        if other.proSocial < 0.0:
            hoarders.append(other)

    if sharers:
        return random.choice(sharers)

    possible_targets = [other for other in eligible if other not in hoarders]
    if not possible_targets:
        return None

    return random.choice(possible_targets)
    
def should_reproduce(agent: Agent, res_needed:float, under1_DeathRate: float) -> bool:

    if agent.age < agent.repAge or agent.age > agent.menoAge:
        print(f"Agent {agent.id}, of age {agent.age} and beh {agent.behavior} is NOT in reproduction age. ")
        return False
    else:   
        skew= agent.resources/res_needed #/ max_storage
        uniform_sample = random.random()
        scaled_sample = uniform_sample * (1.0 + skew / 2.0)
        sample = (2.0 * scaled_sample) / (1.0 + np.sqrt(1.0 + 2.0 * skew * scaled_sample))
    
        print(f"Agent {agent.id}, age {agent.age}, beh. {agent.behavior}, res. {agent.resources:.2f},  slope {skew:.2f} is considering reproduction. Sample: {sample:.1f}")
        return sample > under1_DeathRate


def simulate(config: Dict[str, object], verbose: bool = False) -> Dict[str, object]:
    agents = init_agents(config)
    ticks = int(config["ticks"])
    needed = float(config["Needed"])
    under1_DeathRate = float(config["Under1DeathRate"])
    max_childs = float(config["MaxChilds"])
    decay = float(config["Decay"])
    prob_beh = float(config["probBeh"])
    chang = float(config["Chang"])
    reNeutral = float(config["ReNeutral"])
    share_fraction = float(config.get("ShareFraction", 0.35))
    base_death_timer = float(config.get("BaseDeathTimer", 3.0))
    max_storage = float(config["MaxStorage"])
    share_th = float(config.get("ShareThreshold", 0.5))
    N = int(config["N"])

    history: List[Dict[str, object]] = []
    environment = "neutral"

    for tick in range(ticks):
        if len(agents)>0: 
            print("tick", tick, '\n')
        environment = advance_environment(environment, chang, reNeutral)
        env_resources = produce_environment_resources(environment, needed, N)

        agents = distribute_resources(env_resources, agents, needed, max_storage)
        
        for agent in agents:
            agent.proSocial *= agent.decay
            agent.maybe_switch_behavior(prob_beh)
            agent.age += 1

        next_generation: List[Agent] = []
        total_reproductions = 0
        total_deaths = 0

        for agent in agents:
            if agent.resources < 0:
                continue  # Skip agents with negative resources

            if agent.resources >= needed and agent.behavior == "share":
                target = choose_target(agent, agents, share_th)
                if target is not None:
                    share_amount = min(agent.resources - needed, share_fraction * max(1.0, agent.resources / max(needed, 1e-6)))
                    if share_amount > 0.0 and agent.resources >= share_amount:
                        agent.resources -= share_amount
                        target.resources += share_amount
                        agent.proSocial += share_amount/needed
                        #if tick % 22 == 0:  print('tick. num', tick, 'prosociual', agent.proSocial)

            if agent.behavior == "hoard":
                # Hoarders recieve and keep their resources and do not share, ptroSociality captures that
                agent.proSocial = (agent.proSocial - (agent.resources - needed)/needed)
        
            reproduction = should_reproduce(agent, needed, under1_DeathRate)
            if  agent.resources > needed and reproduction:
                
                sigma = max(0.1, min(1.5, agent.resources / max(needed, 1e-6)))
                reproduction_chance = int(abs(random.normalvariate(mu=max_childs, sigma=sigma))+0.5)
                available_resources = agent.resources - needed*(reproduction_chance+1)
                reproduction_events = max(int(available_resources / needed), int((agent.resources - needed)/needed) )
               
                for _ in range(reproduction_events):
                    total_reproductions += reproduction_events
                    child_behavior = agent.behavior

                    child = Agent(
                        agent_id=buffer + len(agents) + len(next_generation),
                        behavior=child_behavior,
                        resources=0.0,
                        decay=decay,
                        repAge=agent.repAge,
                        menoAge=agent.menoAge,
                        death_timer=random.uniform(1, float(config["BaseDeathTimer"])),
                        age=0,
                    )
                    next_generation.append(child)
            
            still_alive = agent.alive()
            if agent.resources >= needed and still_alive:
                agent.death_timer = random.uniform(agent.death_timer, base_death_timer)
                agent.resources = 1#needed#min(needed, agent.resources)
                next_generation.append(agent)
            else:
                agent.death_timer -= 1.0
                if agent.death_timer >= 0.0 and still_alive:
                    agent.resources = 1
                    next_generation.append(agent)
                    
                else:
                    total_deaths += 1
                    print(f"Agent {agent.id} has died at age {agent.age} with resources {agent.resources:.2f} and death timer {agent.death_timer:.2f}.")
        proSociality = sum(agent.proSocial for agent in agents)
        history.append(
            {
                "tick": tick,
                "environment": environment,
                "resources_produced": round(env_resources, 3),
                "population": len(agents),
                "behavior_counts": {behavior: sum(1 for agent in agents if agent.behavior == behavior) for behavior in ["share", "hoard"]},
                "proSociality": proSociality,
                "agents": [agent.to_dict() for agent in agents],
            }
        )
        agents = next_generation
        #if verbose and tick % 1 == 0 and len(agents)>0:
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
