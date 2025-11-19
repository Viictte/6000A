import requests
import os
import json
import time
from PIL import Image, ImageDraw, ImageFont
import textwrap
from config import Config

class ComicGenerator:
    """Comic Generator Class"""
    
    def __init__(self):
        # Use absolute paths to ensure saving to correct location
        # Get parent directory of backend directory (project root)
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_root = os.path.dirname(backend_dir)
        self.output_dir = os.path.join(project_root, "frontend", "static", "generated_comics")
        
        os.makedirs(self.output_dir, exist_ok=True)
        print(f" Comic save directory: {self.output_dir}")
        
        self.api_key = Config.DASHSCOPE_API_KEY
        self.image_api_url = Config.DASHSCOPE_IMAGE_API

    def _clean_text_for_render(self, text):
        """Strip characters that the default PIL bitmap font cannot render."""
        if not text:
            return ''

        # Keep standard ASCII/latin-1 glyphs so fallback fonts never raise
        safe_chars = ''.join(ch for ch in text if ord(ch) <= 255)
        if safe_chars.strip():
            return safe_chars

        # If everything was stripped (e.g., complex script), return the original so
        # custom fonts can still attempt to render it.
        return text
    
    def create_comic(self, steps, comic_id, image_style='<anime>'):
        """Create complete comic"""
        comic_panels = []
        
        for i, step in enumerate(steps):
            panel_path = self.create_panel_with_ai_image(step, comic_id, i, image_style)
            comic_panels.append(panel_path)
        
        # Combine panels to create final comic
        final_comic_path = self.combine_panels(comic_panels, comic_id)
        return final_comic_path
    
    def create_panel_with_ai_image(self, step, comic_id, panel_index, image_style='<anime>'):
        """Create comic panel with AI image using Tongyi Wanxiang"""
        try:
            # Generate image
            image_path = self.generate_ai_image(step, comic_id, panel_index, image_style)
            
            if image_path and os.path.exists(image_path):
                # If AI image generation successful, add text to image
                return self.add_text_to_image(image_path, step, comic_id, panel_index)
            else:
                # If AI image generation fails, use original simple drawing method
                return self.create_panel(step, comic_id, panel_index)
                
        except Exception as e:
            print(f"AI image generation failed: {e}")
            # Fallback to original method
            return self.create_panel(step, comic_id, panel_index)
    
    def generate_ai_image(self, step, comic_id, panel_index, image_style='<anime>'):
        """Generate image using Tongyi Wanxiang (async mode)"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
                'X-DashScope-Async': 'enable'
            }
            
            # Build English dynamic prompt
            character_desc = step.get('character_description', 'cute cartoon child with big eyes, casual clothes')
            action_scene = step.get('action_scene', 'performing action with hands')
            step_desc = step.get('description', '')
            
            # Combine into vivid scene description (all English)
            prompt = f"{character_desc}, {action_scene}, {step_desc}, bright colors, simple background, child-friendly, safe content, dynamic pose, expressive face, indoor scene"
            
            payload = {
                "model": "wanx-v1",
                "input": {
                    "prompt": prompt,
                    "negative_prompt": "violence, adult content, horror, blood, inappropriate for children, static pose, stiff, standing straight, arms at sides, boring"
                },
                "parameters": {
                    "style": image_style,  # Use user-selected style
                    "size": "1024*1024",  # Square, suitable for comic panels
                    "n": 1
                }
            }
            
            print(f"Generating image - Style: {image_style}")
            print(f"Prompt: {prompt[:150]}...")
            response = requests.post(self.image_api_url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                # Async mode, get task_id
                if 'output' in result and 'task_id' in result['output']:
                    task_id = result['output']['task_id']
                    print(f"Task created, task_id: {task_id}")
                    
                    # Poll for result
                    image_url = self.poll_task_result(task_id)
                    if image_url:
                        return self.download_image(image_url, comic_id, panel_index)
                else:
                    print(f"Unexpected response format: {result}")
            else:
                print(f"API call failed: {response.status_code}, {response.text}")
            
            return None
            
        except Exception as e:
            print(f"Tongyi Wanxiang API call failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def poll_task_result(self, task_id, max_attempts=30):
        """Poll task result"""
        get_url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
        headers = {
            'Authorization': f'Bearer {self.api_key}'
        }
        
        for attempt in range(max_attempts):
            try:
                time.sleep(2)  # Wait 2 seconds before querying
                response = requests.get(get_url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    result = response.json()
                    task_status = result.get('output', {}).get('task_status')
                    
                    print(f"Task status [{attempt+1}/{max_attempts}]: {task_status}")
                    
                    if task_status == 'SUCCEEDED':
                        image_url = result['output']['results'][0]['url']
                        print(f"Image generation successful: {image_url}")
                        return image_url
                    elif task_status == 'FAILED':
                        print(f"Task failed: {result}")
                        return None
                    # PENDING or RUNNING continue waiting
                else:
                    print(f"Query task status failed: {response.status_code}")
                    
            except Exception as e:
                print(f"Polling exception: {e}")
        
        print(f"Task timeout, attempted {max_attempts} times")
        return None
    
    def download_image(self, image_url, comic_id, panel_index):
        """Download generated image"""
        try:
            print(f"Downloading image...")
            response = requests.get(image_url, timeout=30)
            if response.status_code == 200:
                image_path = f"{self.output_dir}/ai_image_{comic_id}_{panel_index}.jpg"
                with open(image_path, 'wb') as f:
                    f.write(response.content)
                
                # Verify file
                if os.path.exists(image_path):
                    file_size = os.path.getsize(image_path)
                    print(f" Image downloaded: {image_path} ({file_size/1024:.2f} KB)")
                    return image_path
                else:
                    print(f" File save failed")
            else:
                print(f" Download failed, status code: {response.status_code}")
        except Exception as e:
            print(f" Download exception: {e}")
            import traceback
            traceback.print_exc()
        
        return None
    
    def add_text_to_image(self, image_path, step, comic_id, panel_index):
        """Add text to AI-generated image"""
        try:
            print(f"Adding text to panel {panel_index+1}...")
            
            # Open image
            img = Image.open(image_path)
            img = img.convert('RGB')
            
            # Resize image to standard panel size
            img = img.resize((400, 300), Image.Resampling.LANCZOS)
            
            draw = ImageDraw.Draw(img)
            
            # Font settings
            try:
                font_title = ImageFont.truetype("arial.ttf", 18)
                font_desc = ImageFont.truetype("arial.ttf", 12)
            except:
                font_title = ImageFont.load_default()
                font_desc = ImageFont.load_default()
            
            # Add semi-transparent background for text
            # Title background
            title_text = self._clean_text_for_render(step.get('title', 'Step'))
            title_bbox = draw.textbbox((0, 0), title_text, font=font_title)
            title_width = title_bbox[2] - title_bbox[0]
            title_height = title_bbox[3] - title_bbox[1]
            
            # Create semi-transparent overlay for text background
            overlay = Image.new('RGBA', img.size, (255, 255, 255, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            
            # Title area background
            title_x = (400 - title_width) // 2
            overlay_draw.rectangle([title_x-5, 5, title_x + title_width + 5, 5 + title_height + 10], 
                                 fill=(255, 255, 255, 200))
            
            # Description area background
            desc_text = self._clean_text_for_render(step.get('description', ''))
            wrapped_text = textwrap.fill(desc_text, width=30)
            lines = wrapped_text.split('\n')
            desc_height = len(lines) * 15
            overlay_draw.rectangle([10, 250, 390, 250 + desc_height + 10], 
                                 fill=(255, 255, 255, 200))
            
            # Merge overlay
            img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
            draw = ImageDraw.Draw(img)
            
            # Draw text
            # Title
            draw.text((title_x, 10), title_text, fill='black', font=font_title)
            
            # Description
            y_offset = 255
            for line in lines:
                draw.text((15, y_offset), line, fill='black', font=font_desc)
                y_offset += 15
            
            # Save final panel
            final_panel_path = f"{self.output_dir}/comic_{comic_id}_panel_{panel_index}.png"
            img.save(final_panel_path, 'PNG')
            
            # Verify save successful
            if os.path.exists(final_panel_path):
                file_size = os.path.getsize(final_panel_path)
                print(f" Panel {panel_index+1} saved: {final_panel_path} ({file_size/1024:.2f} KB)")
                return final_panel_path
            else:
                print(f" Panel {panel_index+1} save failed")
                return None
            
        except Exception as e:
            print(f" Text addition failed: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to original method
            return self.create_panel(step, comic_id, panel_index)
    
    def create_panel(self, step, comic_id, panel_index):
        """Create single comic panel (original method as backup)"""
        # Create canvas
        width, height = 400, 300
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)
        
        # Draw border
        draw.rectangle([5, 5, width-5, height-5], outline='black', width=3)
        
        # Add title
        try:
            font_title = ImageFont.truetype("arial.ttf", 20)
            font_desc = ImageFont.truetype("arial.ttf", 14)
        except:
            font_title = ImageFont.load_default()
            font_desc = ImageFont.load_default()
        
        # Draw title
        title_text = self._clean_text_for_render(step.get('title', 'Step'))
        title_bbox = draw.textbbox((0, 0), title_text, font=font_title)
        title_x = (width - (title_bbox[2] - title_bbox[0])) // 2
        draw.text((title_x, 20), title_text, fill='black', font=font_title)
        
        # Draw description text
        desc_text = self._clean_text_for_render(step.get('description', ''))
        wrapped_text = textwrap.fill(desc_text, width=35)
        
        y_offset = 60
        for line in wrapped_text.split('\n'):
            line_bbox = draw.textbbox((0, 0), line, font=font_desc)
            line_x = (width - (line_bbox[2] - line_bbox[0])) // 2
            draw.text((line_x, y_offset), line, fill='black', font=font_desc)
            y_offset += 25
        
        # Draw simple icon
        self._draw_simple_icon(draw, step, width, height)
        
        # Save panel
        panel_path = f"{self.output_dir}/comic_{comic_id}_panel_{panel_index}.png"
        img.save(panel_path)
        
        return panel_path
    
    def _draw_simple_icon(self, draw, step, width, height):
        """Draw simple icon"""
        # Draw different simple icons based on step content
        center_x, center_y = width // 2, height // 2 + 50
        
        if 'brush' in step['description'].lower() or 'tooth' in step['description'].lower():
            # Draw toothbrush icon
            draw.rectangle([center_x-30, center_y-10, center_x+30, center_y+10], fill='lightblue', outline='blue')
            draw.ellipse([center_x-40, center_y-5, center_x-30, center_y+5], fill='white', outline='blue')
        elif 'wash' in step['description'].lower() or 'hand' in step['description'].lower():
            # Draw hand icon
            draw.ellipse([center_x-25, center_y-15, center_x+25, center_y+15], fill='peachpuff', outline='black')
        else:
            # Default star icon
            points = []
            for i in range(5):
                angle = i * 72 - 90
                x = center_x + 20 * (1 if i % 2 == 0 else 0.5) * \
                    (1 if i % 2 == 0 else 1) * (1 if angle < 180 else -1)
                y = center_y + 20 * (1 if i % 2 == 0 else 0.5) * \
                    (1 if i % 2 == 0 else 1) * (1 if angle > 90 else -1)
                points.extend([x, y])
            draw.polygon(points, fill='gold', outline='orange')
    
    def combine_panels(self, panel_paths, comic_id):
        """Combine panels into complete comic"""
        if not panel_paths:
            print(" No panels to combine")
            return None
        
        print(f"\nStarting to combine {len(panel_paths)} panels...")
        
        # Calculate final image dimensions
        panel_width = 400
        panel_height = 300
        cols = min(2, len(panel_paths))
        rows = (len(panel_paths) + cols - 1) // cols
        
        final_width = cols * panel_width
        final_height = rows * panel_height
        
        print(f"Final image dimensions: {final_width}x{final_height} (rows:{rows}, cols:{cols})")
        
        # Create final image
        final_img = Image.new('RGB', (final_width, final_height), color='white')
        
        # Paste panels
        success_count = 0
        for i, panel_path in enumerate(panel_paths):
            if panel_path and os.path.exists(panel_path):
                try:
                    panel_img = Image.open(panel_path)
                    # Ensure panel size is correct
                    if panel_img.size != (panel_width, panel_height):
                        panel_img = panel_img.resize((panel_width, panel_height), Image.Resampling.LANCZOS)
                    
                    x = (i % cols) * panel_width
                    y = (i // cols) * panel_height
                    final_img.paste(panel_img, (x, y))
                    print(f"   Panel {i+1} pasted to position ({x}, {y})")
                    success_count += 1
                except Exception as e:
                    print(f"   Panel {i+1} paste failed: {e}")
            else:
                print(f"    Panel {i+1} does not exist: {panel_path}")
        
        if success_count == 0:
            print("No panels successfully pasted")
            return None
        
        # Save final comic
        final_path = f"{self.output_dir}/comic_{comic_id}_final.png"
        final_img.save(final_path, 'PNG', quality=95)
        
        print(f"\nFinal comic saved: {final_path}")
        print(f"   Successfully combined {success_count}/{len(panel_paths)} panels")
        
        # Verify file actually exists
        if os.path.exists(final_path):
            file_size = os.path.getsize(final_path)
            print(f"   File size: {file_size/1024:.2f} KB")
            return final_path
        else:
            print(f"Warning: File save failed")
            return None