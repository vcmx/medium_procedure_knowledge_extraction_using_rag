## Relevant Files

- `src/modules/pipeline/multimodal_rag_pipeline.py` - Main pipeline script that was refactored to use factories.
- `src/modules/image_processor/factory.py` - Refactored to a single factory for creating all image processors.
- `src/modules/embeddings/factory.py` - Updated to include the Hugging Face Hub embedder.
- `src/modules/image_processor/florence_huggingface_processor.py` - New processor for generating captions via the Hugging Face API.
- `src/modules/embeddings/huggingface_hub.py` - New embedder for generating embeddings via the Hugging Face API.
- `src/modules/image_processor/base.py` - New base class to define a common interface for image processors.
- `src/modules/utils/image_utils.py` - New utility file for image-related helpers.
- `run_evaluation_app.py` - New Streamlit application for running evaluations.
- `src/modules/evaluation/evaluator.py` - Module containing the core evaluation logic refactored from the notebook.
- `src/modules/query/engine.py` - New module to handle querying the RAG storage.
- `src/modules/evaluation/evaluation_test_cases.json` - JSON file to store and manage evaluation test cases.
- `requirements.txt` - To add new dependencies like `deepeval`.
- `.env` - Used for storing the `HUGGINGFACE_API_KEY`, `OPENROUTER_API_KEY`. Not to be committed. Use `.env.example` as template.

### Notes

- The goal of this refactor is to offload compute-intensive tasks (captioning, embedding) to the Hugging Face Inference API to improve performance during the data preparation phase.
- An `HUGGINGFACE_API_KEY` must be present in a `.env` file for the Hugging Face implementations to work.

## Tasks

- [x] 1.0 Refactor Pipeline to Use Hugging Face for Performance
  - [x] 1.1 Create `BaseImageProcessor` abstract class in `src/modules/image_processor/base.py` to define a common interface for all image processors.
  - [x] 1.2 Create `FlorenceHuggingFaceImageProcessor` in `src/modules/image_processor/florence_huggingface_processor.py` to generate captions via the Hugging Face API.
  - [x] 1.3 Update `FlorenceLocalImageProcessor` to inherit from `BaseImageProcessor` for consistency.
  - [x] 1.4 Create `image_to_base64` utility in `src/modules/utils/image_utils.py` for the HF API embedder.
  - [x] 1.5 Create `HuggingFaceHubEmbedder` in `src/modules/embeddings/huggingface_hub.py` to generate embeddings via the Hugging Face API.
  - [x] 1.6 Refactor `src/modules/image_processor/factory.py` into a unified `ImageProcessorFactory` class that can create 'local', 'huggingface', or 'openrouter' processors.
  - [x] 1.7 Update `src/modules/embeddings/factory.py` to include the new `HuggingFaceHubEmbedder`.
  - [x] 1.8 Refactor `src/modules/pipeline/multimodal_rag_pipeline.py` to use the factories, allowing runtime selection of different implementations.
  - [x] 1.9 Update Hugging Face clients to load the API key from the `.env` file.
- [ ] 2.0 Setup Remaining RAG Pipeline Infrastructure
- [ ] 3.0 Enhance PDF Document Ingestion and Processing
- [ ] 4.0 Implement and Refine the Query Engine and Chat Interface
- [ ] 5.0 Develop Agentic Capabilities for Extended Search
- [ ] 6.0 Integrate and Test the End-to-End System
- [x] 7.0 Implement a User-Friendly Evaluation Application
  - [x] 7.1 Create `evaluation_test_cases.json` in `src/modules/evaluation` and populate it with the four test cases from the `procedure_eval_deepeval.ipynb` notebook.
  - [x] 7.2 Create the query engine module in `src/modules/query/engine.py` to load the RAG index from storage and execute queries.
  - [x] 7.3 Refactor the evaluation logic from the notebook into a reusable module at `src/modules/evaluation/evaluator.py`.
  - [x] 7.4 Build the core UI for the evaluation Streamlit app in `run_evaluation_app.py`, including a dropdown to select test cases and a button to trigger evaluation.
  - [x] 7.5 Integrate the query engine and evaluator with the Streamlit app to run end-to-end evaluations on a selected test case.
  - [x] 7.6 Implement the test case editor in the Streamlit app, allowing users to add, edit, and delete test cases from the `evaluation_test_cases.json` file.
  - [x] 7.7 Add `deepeval` to the project's dependencies and ensure the `OPENAI_API_KEY` is loaded from the `.env` file.
  - [x] 7.8 Align embedder implementation options in `run_evaluation_app.py` with those in `src/modules/query_answering/rag_chat_app.py`.
  - [x] 7.9 Add a slider to control the 'Number of results to retrieve' (`n_results`) in the sidebar of `run_evaluation_app.py`.
  - [x] 7.10 Add a checkbox to toggle 'Use MMR for diversity' in the sidebar of `run_evaluation_app.py`.
  - [x] 7.11 Add filter inputs for 'Page Number' and 'Title' in the sidebar of `run_evaluation_app.py`.
  - [x] 7.12 Add a dropdown to select 'Experience Level' in the sidebar of `run_evaluation_app.py`.
  - [x] 7.13 Update the `query_engine.query` call within `run_evaluation_app.py` to utilize the new configuration options (n_results, MMR, filters, and experience level).