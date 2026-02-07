"""
Test suite photo registry.

Manages a set of diverse test photos with metadata for systematic benchmarking.
Photos should be placed in input/test_suite/.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class TestPhoto:
    filename: str
    description: str
    age_group: str  # child, teen, adult, elderly
    skin_tone: str  # light, medium, dark
    group_size: int  # 1 = solo, 2+ = group
    has_glasses: bool = False
    lighting: str = "good"  # good, dim, backlit, mixed
    tags: List[str] = field(default_factory=list)

    @property
    def path(self) -> str:
        return str(Path("input/test_suite") / self.filename)

    @property
    def exists(self) -> bool:
        return Path(self.path).is_file()


# Register test photos here as they're added to input/test_suite/
TEST_PHOTOS: List[TestPhoto] = [
    TestPhoto(
        filename="child_light_good.jpg",
        description="Young child, light skin, good indoor lighting",
        age_group="child",
        skin_tone="light",
        group_size=1,
        lighting="good",
        tags=["baseline"],
    ),
    TestPhoto(
        filename="adult_medium_glasses.jpg",
        description="Adult with glasses, medium skin tone",
        age_group="adult",
        skin_tone="medium",
        group_size=1,
        has_glasses=True,
        lighting="good",
        tags=["glasses", "baseline"],
    ),
    TestPhoto(
        filename="teen_dark_outdoor.jpg",
        description="Teenager, dark skin, outdoor natural light",
        age_group="teen",
        skin_tone="dark",
        group_size=1,
        lighting="good",
        tags=["outdoor"],
    ),
    TestPhoto(
        filename="elderly_light_indoor.jpg",
        description="Elderly person, light skin, indoor lighting",
        age_group="elderly",
        skin_tone="light",
        group_size=1,
        lighting="dim",
        tags=["elderly", "dim_lighting"],
    ),
    TestPhoto(
        filename="child_dark_backlit.jpg",
        description="Young child, dark skin, backlit/challenging lighting",
        age_group="child",
        skin_tone="dark",
        group_size=1,
        lighting="backlit",
        tags=["challenging"],
    ),
    TestPhoto(
        filename="group_mixed_2.jpg",
        description="Two people, mixed ages/tones",
        age_group="adult",
        skin_tone="medium",
        group_size=2,
        lighting="good",
        tags=["group"],
    ),
    TestPhoto(
        filename="adult_medium_dim.jpg",
        description="Adult, medium skin, dim/evening lighting",
        age_group="adult",
        skin_tone="medium",
        group_size=1,
        lighting="dim",
        tags=["dim_lighting"],
    ),
]


def get_available_photos() -> List[TestPhoto]:
    """Return only photos that exist on disk."""
    return [p for p in TEST_PHOTOS if p.exists]


def get_photos_by_tag(tag: str) -> List[TestPhoto]:
    """Filter photos by tag."""
    return [p for p in TEST_PHOTOS if tag in p.tags and p.exists]


def get_photo_paths() -> List[str]:
    """Return paths of all available test photos."""
    return [p.path for p in get_available_photos()]


def print_suite_status():
    """Print the status of all registered test photos."""
    print(f"Test Suite: {len(TEST_PHOTOS)} registered, {len(get_available_photos())} available\n")
    for photo in TEST_PHOTOS:
        status = "OK" if photo.exists else "MISSING"
        print(f"  [{status}] {photo.filename}")
        print(f"         {photo.description}")
        print(f"         age={photo.age_group} skin={photo.skin_tone} group={photo.group_size} glasses={photo.has_glasses} light={photo.lighting}")
    print()
    missing = [p for p in TEST_PHOTOS if not p.exists]
    if missing:
        print(f"Add {len(missing)} missing photos to input/test_suite/ to complete the suite.")


if __name__ == "__main__":
    print_suite_status()
