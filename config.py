import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_PERSON_URN = os.getenv("LINKEDIN_PERSON_URN")

QUOTES_FILE = "used_quotes.json"
IMAGES_DIR = "generated_images"

# Time to post daily (24h format)
POST_TIME = "09:00"

# Background-only styles for Imagen 3 — no text, clean open sky/space at top for overlay
IMAGE_STYLES = [
    "golden sunrise over a winding road through vast rolling hills, dramatic sky with clouds, cinematic landscape photography, open sky at top",
    "misty mountain peaks at dawn, serene peaceful valley, soft morning light, open sky at top, photorealistic",
    "deep space nebula with vibrant purple and blue colors, stars and cosmic dust, digital art, open space at top",
    "minimalist dark navy background with soft golden light rays emanating from center, clean and modern",
    "lush ancient forest path with sunlight shafts filtering through tall trees, magical atmosphere, open canopy",
    "calm ocean at sunset with warm orange and pink reflections, horizon visible, photorealistic photography",
    "snow-capped mountain range with dramatic storm clouds and rays of light, epic landscape photography",
    "tranquil lake at dawn with mirror-perfect reflections and soft morning fog, open sky visible",
    "vast desert sand dunes at golden hour with sweeping shadows and rich textures, open sky at top",
    "northern lights aurora borealis in vivid green and purple over a frozen silent landscape",
    "towering ancient redwood forest with golden light shafts piercing the high canopy, open top",
    "Mediterranean cliff coastline at sunrise with calm blue water below, dramatic sky above",
    "rolling green Irish hills under a dramatic moody cloudscape, wide open sky",
    "autumn forest path with red and golden fallen leaves, warm bokeh light, open sky through trees",
    "volcanic island at twilight with glowing horizon and dark dramatic sky above",
]
