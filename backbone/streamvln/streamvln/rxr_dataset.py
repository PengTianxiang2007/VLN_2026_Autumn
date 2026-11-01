"""RxR VLN-CE Guide episodes for the English val_unseen benchmark."""

import gzip
import json
import os

from habitat.core.dataset import Dataset
from habitat.core.registry import registry
from habitat.tasks.nav.nav import NavigationGoal
from habitat.tasks.vln.vln import InstructionData, VLNEpisode


LANGUAGES = frozenset(("en-US", "en-IN"))
SCENE_PREFIX = "data/scene_datasets/"


@registry.register_dataset(name="RxRVLN-English-v1")
class RxREnglishGuideDataset(Dataset):
    """Load RxR Guide episodes without altering the published archive."""

    @staticmethod
    def check_config_paths_exist(config):
        return os.path.isfile(config.data_path.format(split=config.split)) and os.path.isdir(
            config.scenes_dir
        )

    def __init__(self, config=None):
        self.episodes = []
        if config is None:
            return

        path = config.data_path.format(split=config.split)
        with gzip.open(path, "rt") as stream:
            data = json.load(stream)

        for record in data["episodes"]:
            if record["info"]["role"] != "guide":
                continue
            instruction = record["instruction"]
            if instruction["language"] not in LANGUAGES:
                continue

            scene_id = record["scene_id"]
            if scene_id.startswith(SCENE_PREFIX):
                scene_id = scene_id[len(SCENE_PREFIX) :]
            episode = VLNEpisode(
                episode_id=str(record["episode_id"]),
                trajectory_id=record["trajectory_id"],
                scene_id=os.path.join(config.scenes_dir, scene_id),
                start_position=record["start_position"],
                start_rotation=record["start_rotation"],
                goals=[NavigationGoal(**goal) for goal in record["goals"]],
                instruction=InstructionData(instruction_text=instruction["instruction_text"]),
                reference_path=[],
                info={"role": "guide", "language": instruction["language"]},
            )
            self.episodes.append(episode)

        self.episodes = list(filter(self.build_content_scenes_filter(config), self.episodes))
