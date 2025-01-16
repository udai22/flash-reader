import fitz  # PyMuPDF
import json
import os
from typing import List, Tuple, Dict
import requests
from dotenv import load_dotenv
import glob
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('pdf_processing.log')
    ]
)

# Load environment variables
load_dotenv()

class DeepSeekAPI:
    """DeepSeek API client wrapper"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.deepseek.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def chat_completion(self, prompt: str) -> Dict:
        """Send a chat completion request to DeepSeek API"""
        endpoint = f"{self.base_url}/chat/completions"
        
        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "model": "deepseek-chat",
            "temperature": 0.7,
            "max_tokens": 2000
        }

        try:
            logging.debug(f"Sending request to DeepSeek API with prompt length: {len(prompt)}")
            response = requests.post(endpoint, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"DeepSeek API request failed: {str(e)}")
            raise Exception(f"DeepSeek API request failed: {str(e)}")

class PDFProcessor:
    def __init__(self, api_key: str):
        self.api_client = DeepSeekAPI(api_key=api_key)
        self.output_dir = "/Users/udaikhattar/Desktop/Development/DeepSeek Research/outputs"
        os.makedirs(self.output_dir, exist_ok=True)
        
    def extract_text_from_pdf(self, pdf_path: str) -> List[Dict]:
        """
        Extract text from each page of the PDF with improved error handling.
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
        try:
            logging.info(f"Opening PDF: {pdf_path}")
            pdf_document = fitz.open(pdf_path)
            pages_text = []

            for page_number in range(len(pdf_document)):
                page = pdf_document[page_number]
                text = page.get_text("text")
                if text.strip():  # Only include non-empty pages
                    pages_text.append({
                        "page_number": page_number + 1,
                        "text": text
                    })
                    logging.debug(f"Extracted {len(text)} characters from page {page_number + 1}")

            logging.info(f"Successfully extracted text from {len(pages_text)} pages")
            return pages_text
        except Exception as e:
            logging.error(f"Error extracting text from PDF: {str(e)}")
            raise Exception(f"Error extracting text from PDF: {str(e)}")
        finally:
            if 'pdf_document' in locals():
                pdf_document.close()

    def chunk_text(self, text: str, max_chunk_size: int = 4000) -> List[str]:
        """
        Split text into smaller chunks to avoid API limits.
        """
        words = text.split()
        chunks = []
        current_chunk = []
        current_size = 0

        for word in words:
            word_size = len(word) + 1  # +1 for space
            if current_size + word_size > max_chunk_size:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_size = word_size
            else:
                current_chunk.append(word)
                current_size += word_size

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        logging.debug(f"Split text into {len(chunks)} chunks")
        return chunks

    def process_with_deepseek(self, page_number: int, text: str) -> Dict:
        """
        Process text chunks with DeepSeek API and combine results.
        """
        chunks = self.chunk_text(text)
        page_results = []

        for i, chunk in enumerate(chunks):
            logging.info(f"Processing chunk {i+1}/{len(chunks)} of page {page_number}")
            
            prompt = (
                f"You are an advanced assistant specialized in structuring books for easy parsing. "
                f"Process the following content from Page {page_number}, chunk {i+1}/{len(chunks)}:\n\n{chunk}\n\n"
                "Please return a valid JSON object with the following structure:\n"
                "{\n"
                "  \"page\": (integer) the page number,\n"
                "  \"chapter\": (string or integer) the chapter title or number if identifiable,\n"
                "  \"content\": (string) the main text of this page in a human-readable format,\n"
                "  \"words\": [\n"
                "    { \"word_number\": (integer), \"word\": (string) }"
                "  ]\n"
                "}\n"
                "Ensure that:\n"
                "1) \"content\" includes all text a human would read on this page.\n"
                "2) \"words\" is a sequential list of all individual words from \"content\".\n"
                "3) You preserve headings within \"content\" if they appear.\n"
                "4) Only return valid JSON.\n"
                "This data must be consistent so we can reconstruct a full, organized version of the book."
            )

            try:
                response = self.api_client.chat_completion(prompt)
                logging.debug(f"Received response for chunk {i+1}")
                print(f"\nInput chunk {i+1}/{len(chunks)} (first 100 chars): {chunk[:100]}...")
                print(f"Output response (first 100 chars): {str(response)[:100]}...")
                page_results.append(response)
            except Exception as e:
                logging.error(f"Error processing chunk {i+1} of page {page_number}: {str(e)}")
                continue

        return {
            "page_number": page_number,
            "deepseek_output": page_results
        }

    def process_pdf(self, pdf_path: str) -> Dict:
        """
        Process a single PDF and return structured output.
        """
        try:
            pdf_name = os.path.basename(pdf_path)
            logging.info(f"Starting processing of PDF: {pdf_name}")
            
            # Extract text from PDF
            extracted_pages = self.extract_text_from_pdf(pdf_path)
            
            # Process each page
            final_results = []
            total_pages = len(extracted_pages)
            
            for i, page_data in enumerate(extracted_pages):
                page_number = page_data["page_number"]
                text = page_data["text"]
                logging.info(f"Processing page {page_number}/{total_pages} of {pdf_name}")
                page_result = self.process_with_deepseek(page_number, text)
                final_results.append(page_result)
                print(f"\nProcessed page {page_number}:")
                print(json.dumps(page_result, indent=2)[:200] + "...")

            # Generate output filename (just PDF name + .json)
            output_file = os.path.join(
                self.output_dir,
                f"{os.path.splitext(pdf_name)[0]}.json"
            )
            
            # Save output
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(final_results, f, ensure_ascii=False, indent=2)
            
            logging.info(f"Processing complete for {pdf_name}. Output saved to {output_file}")
            return {"pdf_name": pdf_name, "output_file": output_file, "pages_processed": total_pages}

        except Exception as e:
            logging.error(f"Error processing PDF {pdf_path}: {str(e)}")
            return {"pdf_name": pdf_name, "error": str(e)}

    def batch_process(self, input_pattern: str) -> List[Dict]:
        """
        Process multiple PDFs matching the input pattern.
        """
        pdf_files = glob.glob(input_pattern)
        if not pdf_files:
            logging.warning(f"No PDF files found matching pattern: {input_pattern}")
            return []

        logging.info(f"Found {len(pdf_files)} PDF files to process")
        results = []

        for pdf_file in pdf_files:
            result = self.process_pdf(pdf_file)
            results.append(result)
            
            # Print summary after each PDF
            if "error" in result:
                print(f"\nFailed to process {result['pdf_name']}: {result['error']}")
            else:
                print(f"\nSuccessfully processed {result['pdf_name']}:")
                print(f"- Pages processed: {result['pages_processed']}")
                print(f"- Output saved to: {result['output_file']}")

        return results

def main():
    # Get API key from environment variable
    api_key = os.getenv("DEEPSEEK_API_KEY", "sk-aa8698fcc31048a4a1a33a8ff378a4b2")
    
    # Initialize processor
    processor = PDFProcessor(api_key)
    
    # Get input pattern from user or use default
    default_pattern = os.path.join(os.getcwd(), "*.pdf")
    input_pattern = input(f"Enter path pattern for PDF files (default: {default_pattern}): ") or default_pattern
    
    # Process PDFs
    results = processor.batch_process(input_pattern)
    
    # Print final summary
    print("\nProcessing Summary:")
    print("-" * 50)
    successful = len([r for r in results if "error" not in r])
    failed = len([r for r in results if "error" in r])
    print(f"Total PDFs processed: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Output directory: {processor.output_dir}")

if __name__ == "__main__":
    main()