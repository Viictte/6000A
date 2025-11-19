import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuration Class"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'storyspark-secret-key'
    
    # Tongyi Qianwen API Configuration
    DASHSCOPE_API_KEY = os.environ.get('DASHSCOPE_API_KEY') or 'sk-834dfe456ef0444a853ec6ba9f24e150'
    
    DATABASE_URL = os.environ.get('DATABASE_URL') or 'data/comics.db'
    UPLOAD_FOLDER = 'static/generated_comics'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # Age Group Configuration
    AGE_GROUPS = {
        '3-5': {'complexity': 'very_simple', 'words_per_step': 10},
        '6-8': {'complexity': 'simple', 'words_per_step': 15},
        '9-12': {'complexity': 'medium', 'words_per_step': 20}
    }
    
    # API Endpoint Configuration
    DASHSCOPE_TEXT_API = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    DASHSCOPE_IMAGE_API = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"