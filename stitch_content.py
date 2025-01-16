import json
import os
import logging
import re
from typing import List, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('content_stitching.log')
    ]
)

class ContentStitcher:
    def __init__(self, input_dir: str = "/Users/udaikhattar/Desktop/Development/DeepSeek Research/outputs"):
        self.input_dir = input_dir
        self.output_dir = os.path.join(os.path.dirname(input_dir), "stitched_content")
        os.makedirs(self.output_dir, exist_ok=True)

    def clean_text(self, text: str) -> str:
        """Clean and format text content."""
        # Remove any remaining JSON or markdown artifacts
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        text = re.sub(r'"words":\s*\[.*?\]', '', text, flags=re.DOTALL)
        text = re.sub(r'"page":\s*\d+,?\s*', '', text)
        text = re.sub(r'"chapter":\s*"[^"]*",?\s*', '', text)
        text = re.sub(r'"content":\s*"', '', text)
        text = text.replace('",', '').replace('"}', '').replace('{', '').replace('}', '')
        
        # Clean up whitespace and special characters
        text = text.replace('\\n', ' ').replace('\\r', ' ').replace('\\t', ' ')
        text = text.replace('\\', '')
        text = re.sub(r'\s+', ' ', text)
        
        # Remove page numbers and figure references
        text = re.sub(r'\b\d+\s*$', '', text)  # Remove trailing numbers
        text = re.sub(r'Figure\s+\d+[:.]\s*.*?(?=\n|$)', '', text)  # Remove figure captions
        text = re.sub(r'List of Figures.*?(?=\n|$)', '', text, flags=re.MULTILINE)
        
        # Remove duplicate chapter titles
        text = re.sub(r'(\n\n[A-Z][A-Z\s\d]+)\s+\1', r'\1', text)
        
        return text.strip()

    def extract_content_from_response(self, response: Dict) -> str:
        """Extract content from a DeepSeek API response."""
        try:
            message_content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            if not message_content:
                return ""

            # Try to find the actual content using various methods
            content = ""
            
            # Method 1: Direct JSON parsing
            try:
                json_content = json.loads(message_content.replace("```json", "").replace("```", ""))
                content = json_content.get("content", "")
            except json.JSONDecodeError:
                # Method 2: Regex extraction
                content_match = re.search(r'"content":\s*"(.*?)(?:"\s*,|\s*"\s*})', message_content, re.DOTALL)
                if content_match:
                    content = content_match.group(1)

            # Clean the extracted content
            return self.clean_text(content)

        except Exception as e:
            logging.debug(f"Error extracting content from response: {str(e)}")
            return ""

    def process_json_file(self, json_path: str) -> str:
        """Process a single JSON file and extract all content in order."""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Sort pages by page number
            data.sort(key=lambda x: x["page_number"])
            
            all_content = []
            current_chapter = None
            
            for page_data in data:
                page_number = page_data["page_number"]
                deepseek_outputs = page_data["deepseek_output"]
                
                page_content = []
                for chunk_response in deepseek_outputs:
                    content = self.extract_content_from_response(chunk_response)
                    if content:
                        # Check if this is a chapter heading
                        if re.match(r'^(?:CHAPTER\s+\d+:?\s*)?[A-Z][A-Z\s\d-]+$', content):
                            if content != current_chapter:
                                current_chapter = content
                                all_content.append(f"\n\n{current_chapter}\n\n")
                            continue
                        
                        # Add the content if it's not just a chapter heading
                        page_content.append(content)
                
                if page_content:
                    # Join content and remove any duplicate text
                    combined_content = " ".join(page_content)
                    # Remove any duplicate sentences that might appear at chunk boundaries
                    sentences = combined_content.split('. ')
                    unique_sentences = []
                    for sentence in sentences:
                        if sentence and sentence not in unique_sentences:
                            unique_sentences.append(sentence)
                    cleaned_content = '. '.join(unique_sentences)
                    
                    all_content.append(cleaned_content)

            # Final cleanup of the complete text
            full_text = "\n\n".join(all_content)
            full_text = re.sub(r'\n{3,}', '\n\n', full_text)  # Remove excessive newlines
            full_text = re.sub(r'(?<=[.!?])\s+(?=[A-Z])', '\n\n', full_text)  # Add paragraph breaks
            
            return full_text.strip()

        except Exception as e:
            logging.error(f"Error processing file {json_path}: {str(e)}")
            return ""

    def stitch_content(self, json_filename: str = None) -> None:
        """Stitch content from all JSON files in input directory or a specific file."""
        try:
            if json_filename:
                json_files = [os.path.join(self.input_dir, json_filename)]
            else:
                json_files = [f for f in os.listdir(self.input_dir) if f.endswith('.json')]
                json_files = [os.path.join(self.input_dir, f) for f in json_files]

            for json_path in json_files:
                logging.info(f"Processing {json_path}")
                
                base_name = os.path.splitext(os.path.basename(json_path))[0]
                output_path = os.path.join(self.output_dir, f"{base_name}.txt")
                
                content = self.process_json_file(json_path)
                
                if content:
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    logging.info(f"Content saved to {output_path}")
                    print(f"\nSuccessfully extracted content to: {output_path}")
                    print(f"\nFirst 500 characters of content:")
                    print("-" * 50)
                    print(content[:500] + "...")
                else:
                    logging.warning(f"No content extracted from {json_path}")

        except Exception as e:
            logging.error(f"Error in stitch_content: {str(e)}")

def main():
    stitcher = ContentStitcher()
    
    print("\nContent Stitching Options:")
    print("1. Process all JSON files in the output directory")
    print("2. Process a specific JSON file")
    
    choice = input("Enter your choice (1 or 2): ").strip()
    
    if choice == "1":
        stitcher.stitch_content()
    elif choice == "2":
        filename = input("Enter the JSON filename (e.g., 'book.json'): ").strip()
        stitcher.stitch_content(filename)
    else:
        print("Invalid choice. Please run again and select 1 or 2.")

if __name__ == "__main__":
    main() 