import os
import json
import logging

# Get base directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(BASE_DIR, 'content_stitching.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ContentStitcher:
    def __init__(self):
        self.output_dir = os.path.join(BASE_DIR, 'stitched_content')
        self.input_dir = os.path.join(BASE_DIR, 'outputs')
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.input_dir, exist_ok=True)

    def stitch_content(self, json_filename):
        """Process a JSON file and create a stitched text file"""
        try:
            # Construct input and output paths
            json_path = os.path.join(self.input_dir, json_filename)
            output_filename = os.path.splitext(json_filename)[0] + '.txt'
            output_path = os.path.join(self.output_dir, output_filename)
            
            logger.info(f"Processing {json_path} -> {output_path}")
            
            if not os.path.exists(json_path):
                logger.error(f"JSON file not found: {json_path}")
                return False
            
            with open(json_path, 'r', encoding='utf-8') as f:
                pages_data = json.load(f)
            
            # Sort pages by page number
            pages_data.sort(key=lambda x: x['page_number'])
            
            with open(output_path, 'w', encoding='utf-8') as f:
                for page_data in pages_data:
                    for response in page_data['deepseek_output']:
                        try:
                            message_content = response['choices'][0]['message']['content']
                            content_data = json.loads(message_content)
                            
                            # Write the content
                            if content_data.get('content'):
                                f.write(content_data['content'].strip())
                                f.write('\n\n')  # Add spacing between pages
                        except (json.JSONDecodeError, KeyError) as e:
                            logger.warning(f"Error processing page {page_data['page_number']}: {str(e)}")
                            continue
            
            logger.info(f"Successfully created {output_path}")
            return True
            
        except Exception as e:
            logger.exception(f"Error in stitch_content: {str(e)}")
            return False 