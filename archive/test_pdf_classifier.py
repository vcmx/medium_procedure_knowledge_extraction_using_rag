from src.modules.pdf_processor.pdf_classifier import classify_pdf


def test_classifier():
    # Test with multiple PDFs
    pdf_paths = [
        "input-pdfs/sample.pdf",
        "input-pdfs/AIrfix1.pdf",
    ]

    for pdf_path in pdf_paths:
        print(f"\n{'=' * 80}")
        print(f"Analyzing PDF: {pdf_path}")
        print(f"{'=' * 80}")

        try:
            # Get classification results
            results = classify_pdf(pdf_path)

            # Print overall results
            print("\nOverall Classification:")
            print(f"Filename: {results['filename']}")
            print(f"Total Pages: {results['total_pages']}")
            print(f"Image-based Pages: {results['image_based_pages']}")
            print(f"Text-based Pages: {results['text_based_pages']}")
            print(f"Empty Pages: {results['empty_pages']}")
            print(f"Image Ratio: {results['image_ratio']:.2%}")
            print(f"Text Ratio: {results['text_ratio']:.2%}")
            print(f"Average Image Ratio: {results['avg_image_ratio']:.2%}")
            print(f"Is Image-based: {results['is_image_based']}")
            print(f"Is Text-based: {results['is_text_based']}")

            # Print detailed page results
            print("\nDetailed Page Analysis:")
            print("-" * 50)
            for page in results["page_results"]:
                print(f"\nPage {page['page_number']}:")
                print(f"  Image Ratio: {page['image_ratio']:.2%}")
                print(f"  Text Ratio: {page['text_ratio']:.2%}")
                print(f"  Is Image-based: {page['is_image_based']}")
                print(f"  Is Text-based: {page['is_text_based']}")
                print(f"  Is Empty: {page['is_empty']}")

        except Exception as e:
            print(f"Error analyzing PDF: {str(e)}")


if __name__ == "__main__":
    test_classifier()
