"""Location detection analyzer using Places365, CLIP landmarks, and GeoEstimation.

Implements a 3-tier location detection approach:
1. Places365 scene classification (indoor/outdoor scene types)
2. CLIP-based landmark detection (famous landmarks with coordinates)
3. GeoEstimation (approximate geographic region estimation)
"""

import asyncio
import json
import logging
from pathlib import Path

import torch
import torch.nn.functional as F
from PIL import Image
from torchvision import transforms

from app.config import settings
from app.services.analysis.base import BaseAnalyzer, TagResult

logger = logging.getLogger(__name__)

# Confidence thresholds for each tier
PLACES365_THRESHOLD = 0.15
LANDMARK_THRESHOLD = 0.25
GEO_THRESHOLD = 0.20

# Famous landmarks database with coordinates
LANDMARKS: list[dict] = [
    # Europe
    {"name": "Eiffel Tower", "city": "Paris", "country": "France", "lat": 48.858, "lon": 2.294},
    {"name": "Colosseum", "city": "Rome", "country": "Italy", "lat": 41.890, "lon": 12.492},
    {"name": "Big Ben", "city": "London", "country": "United Kingdom", "lat": 51.501, "lon": -0.125},
    {"name": "Sagrada Familia", "city": "Barcelona", "country": "Spain", "lat": 41.404, "lon": 2.174},
    {"name": "Acropolis", "city": "Athens", "country": "Greece", "lat": 37.971, "lon": 23.726},
    {"name": "Brandenburg Gate", "city": "Berlin", "country": "Germany", "lat": 52.516, "lon": 13.378},
    {"name": "Tower Bridge", "city": "London", "country": "United Kingdom", "lat": 51.505, "lon": -0.075},
    {"name": "Leaning Tower of Pisa", "city": "Pisa", "country": "Italy", "lat": 43.723, "lon": 10.397},
    {"name": "Notre Dame", "city": "Paris", "country": "France", "lat": 48.853, "lon": 2.350},
    {"name": "Stonehenge", "city": "Wiltshire", "country": "United Kingdom", "lat": 51.179, "lon": -1.826},
    {"name": "Neuschwanstein Castle", "city": "Schwangau", "country": "Germany", "lat": 47.558, "lon": 10.750},
    {"name": "Charles Bridge", "city": "Prague", "country": "Czech Republic", "lat": 50.086, "lon": 14.411},
    {"name": "Hagia Sophia", "city": "Istanbul", "country": "Turkey", "lat": 41.009, "lon": 28.980},
    {"name": "Trevi Fountain", "city": "Rome", "country": "Italy", "lat": 41.901, "lon": 12.483},
    {"name": "Windmills of Kinderdijk", "city": "Kinderdijk", "country": "Netherlands", "lat": 51.884, "lon": 4.638},
    {"name": "Edinburgh Castle", "city": "Edinburgh", "country": "United Kingdom", "lat": 55.949, "lon": -3.200},
    {"name": "Santorini", "city": "Santorini", "country": "Greece", "lat": 36.393, "lon": 25.461},
    {"name": "Kremlin", "city": "Moscow", "country": "Russia", "lat": 55.752, "lon": 37.615},
    # Americas
    {"name": "Statue of Liberty", "city": "New York", "country": "United States", "lat": 40.689, "lon": -74.045},
    {"name": "Golden Gate Bridge", "city": "San Francisco", "country": "United States", "lat": 37.820, "lon": -122.478},
    {"name": "Machu Picchu", "city": "Cusco", "country": "Peru", "lat": -13.163, "lon": -72.545},
    {"name": "Christ the Redeemer", "city": "Rio de Janeiro", "country": "Brazil", "lat": -22.952, "lon": -43.211},
    {"name": "CN Tower", "city": "Toronto", "country": "Canada", "lat": 43.643, "lon": -79.387},
    {"name": "Grand Canyon", "city": "Arizona", "country": "United States", "lat": 36.107, "lon": -112.113},
    {"name": "Niagara Falls", "city": "Niagara Falls", "country": "United States", "lat": 43.078, "lon": -79.075},
    {"name": "Chichen Itza", "city": "Yucatan", "country": "Mexico", "lat": 20.683, "lon": -88.569},
    {"name": "Times Square", "city": "New York", "country": "United States", "lat": 40.758, "lon": -73.986},
    {"name": "Mount Rushmore", "city": "South Dakota", "country": "United States", "lat": 43.879, "lon": -103.459},
    {"name": "White House", "city": "Washington DC", "country": "United States", "lat": 38.898, "lon": -77.036},
    {"name": "Hollywood Sign", "city": "Los Angeles", "country": "United States", "lat": 34.134, "lon": -118.322},
    # Asia
    {"name": "Great Wall of China", "city": "Beijing", "country": "China", "lat": 40.432, "lon": 116.570},
    {"name": "Taj Mahal", "city": "Agra", "country": "India", "lat": 27.175, "lon": 78.042},
    {"name": "Mount Fuji", "city": "Honshu", "country": "Japan", "lat": 35.361, "lon": 138.727},
    {"name": "Angkor Wat", "city": "Siem Reap", "country": "Cambodia", "lat": 13.412, "lon": 103.867},
    {"name": "Petronas Towers", "city": "Kuala Lumpur", "country": "Malaysia", "lat": 3.158, "lon": 101.712},
    {"name": "Sydney Opera House", "city": "Sydney", "country": "Australia", "lat": -33.857, "lon": 151.215},
    {"name": "Forbidden City", "city": "Beijing", "country": "China", "lat": 39.916, "lon": 116.397},
    {"name": "Sensoji Temple", "city": "Tokyo", "country": "Japan", "lat": 35.715, "lon": 139.797},
    {"name": "Marina Bay Sands", "city": "Singapore", "country": "Singapore", "lat": 1.283, "lon": 103.861},
    {"name": "Borobudur", "city": "Java", "country": "Indonesia", "lat": -7.608, "lon": 110.204},
    {"name": "Terracotta Army", "city": "Xi'an", "country": "China", "lat": 34.384, "lon": 109.278},
    {"name": "Gardens by the Bay", "city": "Singapore", "country": "Singapore", "lat": 1.282, "lon": 103.864},
    {"name": "Fushimi Inari Shrine", "city": "Kyoto", "country": "Japan", "lat": 34.967, "lon": 135.773},
    # Africa / Middle East
    {"name": "Pyramids of Giza", "city": "Giza", "country": "Egypt", "lat": 29.979, "lon": 31.134},
    {"name": "Burj Khalifa", "city": "Dubai", "country": "United Arab Emirates", "lat": 25.197, "lon": 55.274},
    {"name": "Table Mountain", "city": "Cape Town", "country": "South Africa", "lat": -33.963, "lon": 18.403},
    {"name": "Petra", "city": "Ma'an", "country": "Jordan", "lat": 30.329, "lon": 35.444},
    {"name": "Sphinx", "city": "Giza", "country": "Egypt", "lat": 29.975, "lon": 31.138},
    {"name": "Burj Al Arab", "city": "Dubai", "country": "United Arab Emirates", "lat": 25.141, "lon": 55.185},
    {"name": "Victoria Falls", "city": "Livingstone", "country": "Zambia", "lat": -17.924, "lon": 25.857},
]

# Geographic regions for GeoEstimation
GEO_REGIONS: list[dict] = [
    {"name": "tropical southeast asia", "lat": 10.0, "lon": 106.0},
    {"name": "mediterranean europe", "lat": 41.0, "lon": 14.0},
    {"name": "northern europe", "lat": 55.0, "lon": 10.0},
    {"name": "east asia", "lat": 35.0, "lon": 120.0},
    {"name": "south asia", "lat": 20.0, "lon": 78.0},
    {"name": "middle east", "lat": 30.0, "lon": 45.0},
    {"name": "sub-saharan africa", "lat": -5.0, "lon": 25.0},
    {"name": "north america urban", "lat": 40.0, "lon": -95.0},
    {"name": "south america", "lat": -15.0, "lon": -55.0},
    {"name": "australia and oceania", "lat": -25.0, "lon": 135.0},
    {"name": "arctic and subarctic", "lat": 65.0, "lon": 20.0},
]


class LocationAnalyzer(BaseAnalyzer):
    """Detects location and scene information from images using 3 tiers.

    Tier 1: Places365 scene classification (beach, mountain, urban, etc.)
    Tier 2: CLIP landmark detection (famous places with coordinates)
    Tier 3: GeoEstimation (approximate region with reverse geocoding)
    """

    def __init__(self) -> None:
        self._places365_model = None
        self._places365_categories: list[str] = []
        self._clip_model = None
        self._clip_preprocess = None
        self._clip_tokenizer = None
        self._landmark_text_features = None
        self._geo_text_features = None
        self._device = "cpu"
        self._places365_transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ])

    async def warmup(self) -> None:
        """Pre-load Places365 and CLIP models."""
        try:
            await self._load_places365()
        except Exception as e:
            logger.warning(f"Failed to load Places365 model: {e}")

        try:
            await self._load_clip()
        except Exception as e:
            logger.warning(f"Failed to load CLIP model: {e}")

    async def analyze(self, image_path: str) -> list[TagResult]:
        """Run all 3 tiers of location analysis on an image.

        Args:
            image_path: Path to the image file to analyze.

        Returns:
            List of TagResult with category='WHERE'.
        """
        tags: list[TagResult] = []

        # Tier 1: Places365 scene classification
        try:
            scene_tags = await self._classify_scene(image_path)
            tags.extend(scene_tags)
        except Exception as e:
            logger.error(f"Places365 classification error: {e}")

        # Tier 2: CLIP landmark detection
        try:
            landmark_tags = await self._detect_landmarks(image_path)
            tags.extend(landmark_tags)
        except Exception as e:
            logger.error(f"CLIP landmark detection error: {e}")

        # Tier 3: GeoEstimation
        try:
            geo_tags = await self._estimate_geo(image_path)
            tags.extend(geo_tags)
        except Exception as e:
            logger.error(f"GeoEstimation error: {e}")

        return tags

    async def _load_places365(self) -> None:
        """Download and load the Places365 ResNet50 model and categories."""
        import urllib.request

        cache_dir = Path(settings.MODEL_CACHE_DIR)
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Download categories file
        categories_file = cache_dir / "categories_places365.txt"
        if not categories_file.exists():
            logger.info("Downloading Places365 categories...")
            url = "https://raw.githubusercontent.com/CSAILVision/places365/master/categories_places365.txt"
            await asyncio.to_thread(
                urllib.request.urlretrieve, url, str(categories_file)
            )

        # Parse categories
        with open(categories_file, "r") as f:
            self._places365_categories = []
            for line in f:
                # Format: /a/airfield 0
                parts = line.strip().split(" ")
                category_path = parts[0]
                # Extract readable name from path like /a/airfield -> airfield
                category_name = category_path.split("/")[-1].replace("_", " ")
                self._places365_categories.append(category_name)

        # Download model weights
        model_file = cache_dir / "resnet50_places365.pth.tar"
        if not model_file.exists():
            logger.info("Downloading Places365 ResNet50 weights...")
            url = "http://places2.csail.mit.edu/models_places365/resnet50_places365.pth.tar"
            await asyncio.to_thread(
                urllib.request.urlretrieve, url, str(model_file)
            )

        # Load model
        from torchvision import models

        model = models.resnet50(num_classes=365)
        checkpoint = torch.load(str(model_file), map_location=self._device, weights_only=False)

        # Handle different checkpoint formats
        state_dict = checkpoint.get("state_dict", checkpoint)
        # Remove 'module.' prefix if present (from DataParallel)
        new_state_dict = {}
        for k, v in state_dict.items():
            name = k.replace("module.", "")
            new_state_dict[name] = v

        model.load_state_dict(new_state_dict)
        model.eval()
        self._places365_model = model
        logger.info("Places365 model loaded successfully")

    async def _load_clip(self) -> None:
        """Load the CLIP model using open_clip."""
        import open_clip

        model, _, preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32", pretrained="laion2b_s34b_b79k"
        )
        tokenizer = open_clip.get_tokenizer("ViT-B-32")

        model.eval()
        self._clip_model = model
        self._clip_preprocess = preprocess
        self._clip_tokenizer = tokenizer

        # Pre-compute text embeddings for landmarks
        landmark_prompts = [f"a photo of {lm['name']}" for lm in LANDMARKS]
        with torch.no_grad():
            tokens = tokenizer(landmark_prompts)
            self._landmark_text_features = model.encode_text(tokens)
            self._landmark_text_features = F.normalize(
                self._landmark_text_features, dim=-1
            )

        # Pre-compute text embeddings for geographic regions
        geo_prompts = [f"a photo taken in {r['name']}" for r in GEO_REGIONS]
        with torch.no_grad():
            tokens = tokenizer(geo_prompts)
            self._geo_text_features = model.encode_text(tokens)
            self._geo_text_features = F.normalize(
                self._geo_text_features, dim=-1
            )

        logger.info("CLIP model loaded successfully")

    async def _classify_scene(self, image_path: str) -> list[TagResult]:
        """Tier 1: Classify scene type using Places365.

        Args:
            image_path: Path to the image file.

        Returns:
            Top scene classifications above threshold as TagResults.
        """
        if self._places365_model is None:
            return []

        img = Image.open(image_path).convert("RGB")
        input_tensor = self._places365_transform(img).unsqueeze(0)

        with torch.no_grad():
            output = self._places365_model(input_tensor)
            probabilities = F.softmax(output, dim=1)[0]

        # Get top-5 predictions above threshold
        top_probs, top_indices = torch.topk(probabilities, 5)
        tags: list[TagResult] = []

        for prob, idx in zip(top_probs, top_indices):
            confidence = float(prob)
            if confidence >= PLACES365_THRESHOLD:
                category_idx = int(idx)
                if category_idx < len(self._places365_categories):
                    scene_label = self._places365_categories[category_idx]
                    tags.append(TagResult(
                        category="WHERE",
                        value=scene_label,
                        confidence=confidence,
                    ))

        return tags

    async def _detect_landmarks(self, image_path: str) -> list[TagResult]:
        """Tier 2: Detect famous landmarks using CLIP similarity.

        Args:
            image_path: Path to the image file.

        Returns:
            Detected landmarks above threshold as TagResults with coordinates.
        """
        if self._clip_model is None or self._landmark_text_features is None:
            return []

        img = Image.open(image_path).convert("RGB")
        img_tensor = self._clip_preprocess(img).unsqueeze(0)

        with torch.no_grad():
            image_features = self._clip_model.encode_image(img_tensor)
            image_features = F.normalize(image_features, dim=-1)

            # Compute cosine similarity against all landmarks
            similarities = (image_features @ self._landmark_text_features.T)[0]

        tags: list[TagResult] = []
        for i, score in enumerate(similarities):
            confidence = float(score)
            if confidence >= LANDMARK_THRESHOLD:
                landmark = LANDMARKS[i]
                bbox_data = json.dumps({
                    "type": "landmark",
                    "city": landmark["city"],
                    "country": landmark["country"],
                    "lat": landmark["lat"],
                    "lon": landmark["lon"],
                })
                tags.append(TagResult(
                    category="WHERE",
                    value=landmark["name"],
                    confidence=confidence,
                    bounding_box=bbox_data,
                ))

        return tags

    async def _estimate_geo(self, image_path: str) -> list[TagResult]:
        """Tier 3: Estimate geographic region using CLIP and reverse geocoding.

        Args:
            image_path: Path to the image file.

        Returns:
            Geographic region estimates above threshold with coordinates.
        """
        if self._clip_model is None or self._geo_text_features is None:
            return []

        img = Image.open(image_path).convert("RGB")
        img_tensor = self._clip_preprocess(img).unsqueeze(0)

        with torch.no_grad():
            image_features = self._clip_model.encode_image(img_tensor)
            image_features = F.normalize(image_features, dim=-1)

            # Compute cosine similarity against geographic regions
            similarities = (image_features @ self._geo_text_features.T)[0]

        tags: list[TagResult] = []
        for i, score in enumerate(similarities):
            confidence = float(score)
            if confidence >= GEO_THRESHOLD:
                region = GEO_REGIONS[i]
                location_value = region["name"]

                # Try reverse geocoding for better location name
                try:
                    location_value = await self._reverse_geocode(
                        region["lat"], region["lon"]
                    )
                except Exception as e:
                    logger.debug(f"Reverse geocoding failed for {region['name']}: {e}")

                bbox_data = json.dumps({
                    "type": "geo_estimate",
                    "lat": region["lat"],
                    "lon": region["lon"],
                    "region": region["name"],
                })
                tags.append(TagResult(
                    category="WHERE",
                    value=location_value,
                    confidence=confidence,
                    bounding_box=bbox_data,
                ))

        return tags

    async def _reverse_geocode(self, lat: float, lon: float) -> str:
        """Reverse geocode coordinates to a human-readable location name.

        Args:
            lat: Latitude.
            lon: Longitude.

        Returns:
            Formatted location string like 'City, Country'.
        """
        from geopy.geocoders import Nominatim

        geolocator = Nominatim(user_agent="photo-tagger")
        location = await asyncio.to_thread(
            geolocator.reverse, f"{lat}, {lon}", language="en"
        )

        if location and location.raw.get("address"):
            address = location.raw["address"]
            city = (
                address.get("city")
                or address.get("town")
                or address.get("state")
                or ""
            )
            country = address.get("country", "")
            if city and country:
                return f"{city}, {country}"
            return country or city

        return f"{lat:.1f}, {lon:.1f}"
