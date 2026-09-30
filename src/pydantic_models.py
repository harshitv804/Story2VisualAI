from typing import List

from pydantic import BaseModel, Field


class StoryValidation(BaseModel):
    valid: bool


class StoryMetadata(BaseModel):
    story_title: str = Field(..., min_length=1)
    synopsis: str = Field(..., min_length=1)
    story_style: str = Field(..., min_length=1)


class Character(BaseModel):
    char_id: str
    name: str
    role: str
    char_desc: str
    char_outfit: str


class CharacterMetadata(BaseModel):
    characters: List[Character]


class Prop(BaseModel):
    prop_id: str
    name: str
    prop_desc: str


class PropMetadata(BaseModel):
    props: List[Prop]


class World(BaseModel):
    world_id: str
    name: str
    world_desc: str


class WorldMetadata(BaseModel):
    worlds: List[World]


class Scene(BaseModel):
    scene_id: str
    scene_desc: str


class SceneMetadata(BaseModel):
    scenes: List[Scene]


class SubScene(BaseModel):
    scene_id: str
    scene_desc: str


class SubSceneMetadata(BaseModel):
    subscenes: List[SubScene]


class SubSceneCheckpoint(SubSceneMetadata):
    """On-disk form, also tracks which parent scenes are already generated."""

    scenes_done: List[str] = Field(default_factory=list)


class SceneIngredient(BaseModel):
    scene_id: str
    char_ids: List[str]
    props: List[str]
    world: str


class SceneIngredientsList(BaseModel):
    ingredients: List[SceneIngredient]


class ImagePrompt(BaseModel):
    image_prompt: str


class CharacterImagePrompt(BaseModel):
    char_id: str
    image_prompt: str


class CharacterImagePromptList(BaseModel):
    prompts: list[CharacterImagePrompt]


class WorldImagePrompt(BaseModel):
    world_id: str
    image_prompt: str


class WorldImagePromptList(BaseModel):
    prompts: list[WorldImagePrompt]


class FinalImagePrompt(BaseModel):
    subscene_id: str
    char_ids: list[str]
    world_id: str
    image_prompt: ImagePrompt


class FinalImagePromptList(BaseModel):
    results: List[FinalImagePrompt]
