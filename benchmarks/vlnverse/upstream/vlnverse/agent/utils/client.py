from typing import Any, Dict, List, Optional

import requests

from vlnverse.configs.agent import AgentCfg, InitRequest, ResetRequest, StepRequest
from vlnverse.evaluator.utils.eval import serialize_obs


class AgentClient:
    """
    Client class for Agent service.
    """

    def __init__(self, config: AgentCfg):
        self.base_url = f'http://{config.server_host}:{config.server_port}'
        self.agent_name = self._initialize_agent(config)

    def _initialize_agent(self, config: AgentCfg) -> str:
        request_data = InitRequest(agent_config=config).model_dump(mode='json')

        response = requests.post(
            url=f'{self.base_url}/agent/init',
            json=request_data,
            headers={'Content-Type': 'application/json'},
        )
        response.raise_for_status()

        return response.json()['agent_name']

    def step(self, obs: List[Dict[str, Any]]) -> List[List[int]]:
        request_data = StepRequest(observation=serialize_obs(obs)).model_dump(mode='json')

        response = requests.post(
            url=f'{self.base_url}/agent/{self.agent_name}/step',
            json=request_data,
            headers={'Content-Type': 'application/json'},
        )
        response.raise_for_status()

        return response.json()['action']

    def reset(self, reset_index: Optional[List] = None, episode_ids=None, episode_seeds=None) -> None:
        payload = ResetRequest(reset_index=reset_index).model_dump(mode='json')
        if episode_ids is not None:
            payload.update(episode_ids=episode_ids, episode_seeds=episode_seeds)
        response = requests.post(
            url=f'{self.base_url}/agent/{self.agent_name}/reset',
            json=payload,
            headers={'Content-Type': 'application/json'},
        )
        response.raise_for_status()
        if episode_ids is not None:
            proof = response.json()
            if proof.get('episode_id') != episode_ids[0] or proof.get('episode_seed') != episode_seeds[0]:
                raise RuntimeError('Agent did not acknowledge the expected episode seed.')
