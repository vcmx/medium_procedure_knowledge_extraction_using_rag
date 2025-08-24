import os

from dotenv import load_dotenv
from llama_parse import LlamaParse

# Load environment variables from .env file
load_dotenv()

# Set your API key here or use environment variable
LLAMA_API_KEY = os.getenv("LLAMA_API_KEY")
if not LLAMA_API_KEY:
    raise ValueError(
        "Please set the LLAMA_API_KEY in your .env file or environment variables"
    )


def convert_pdf_to_markdown_and_json(pdf_path, output_dir="./llama-parser-output"):
    """
    Convert a PDF file to both markdown and JSON formats using llama-parse.

    Args:
        pdf_path (str): Path to the PDF file
        output_dir (str): Directory to save the output files
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Get the base filename without extension
    base_filename = os.path.splitext(os.path.basename(pdf_path))[0]

    # Initialize parsers with API key
    not_from_cache = False
    parser_txt = LlamaParse(
        api_key=LLAMA_API_KEY,
        verbose=True,
        invalidate_cache=not_from_cache,
        result_type="text",
    )
    parser_md = LlamaParse(
        api_key=LLAMA_API_KEY,
        verbose=True,
        invalidate_cache=not_from_cache,
        result_type="markdown",
    )

    # Parse the PDF
    print(f"Converting {pdf_path} to markdown and JSON...")

    # Get text output
    print("Parsing text...")
    docs_text = parser_txt.load_data(pdf_path)
    text_output_path = os.path.join(output_dir, f"{base_filename}.txt")
    with open(text_output_path, "w", encoding="utf-8") as f:
        f.write(str(docs_text))
    print(f"Text file saved to: {text_output_path}")

    # Get markdown output
    print("Parsing markdown...")
    md_json_objs = parser_md.get_json_result(pdf_path)
    md_json_list = md_json_objs[0]["pages"]

    # Save markdown JSON
    md_output_path = os.path.join(output_dir, f"{base_filename}.json")
    with open(md_output_path, "w", encoding="utf-8") as f:
        f.write(str(md_json_list))
    print(f"Markdown JSON file saved to: {md_output_path}")


if __name__ == "__main__":
    # Example usage
    pdf_file = "./13 subaru engine imp04_sec2_4-2.pdf"
    convert_pdf_to_markdown_and_json(pdf_file)
