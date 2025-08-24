import logging
import os
import re
from typing import List, Tuple

from datasets import Dataset
from deepeval.metrics import GEval
from deepeval.metrics.g_eval import Rubric
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from ragas.llms import LangchainLLMWrapper

load_dotenv(override=True)

# Set up logging
logger = logging.getLogger(__name__)

# RAGAS imports
from ragas import evaluate as ragas_evaluate
from ragas.metrics import answer_relevancy, context_precision, faithfulness, answer_similarity, answer_correctness, context_recall


class Evaluator:
    """A reusable evaluator for assessing procedural text quality."""

    def __init__(self):
        """
        Initializes the Evaluator, setting up API keys and defining criteria.
        """
        # Ensure API key is available
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError(
                "OPENAI_API_KEY not found in environment variables. Please add it to your .env file."
            )
        self.logger = logging.getLogger(__name__)
        self.criteria = self._define_criteria()
        self.rubrics = self._define_rubrics()

    def _define_criteria(self) -> dict:
        """Defines the evaluation criteria."""
        return {
            "Step-by-Step Accuracy": "Output should include all procedural steps from the source. All steps are in the correct order. There should not be any missing, added or modified steps that may result in user error or damage.",
            "Terminology Fidelity": "Technical terms from source should be preserved. Use domain-specific vocabulary.",
            "Handling of Warnings and Cautions": "Safety warnings and cautions should be clearly flagged. Risk-related statements should be placed near the relevant steps.",
            "Precision in instructions": "Where it applies, instructions should provide user clear numerical measure of the required specifications. For example, a procedure involving inspection should indicate exactly what to look out for (e.g., rust, dirt, damage etc).",
            "Closed Loop Procedural": "Procedural instructions should result in a closed loop. For example, a procedure involving the removal of a component should eventually be closed with the reinstallation of the component.",
            "Accuracy with Ground Truth (Expected output)": "The generated output should closely match the expected output provided in the test case, with a strong emphasis on preserving both meaning and relevance",
        }

    def _define_rubrics(self) -> List[Rubric]:
        """Defines the scoring rubrics for evaluation."""
        return [
            Rubric(
                score_range=(0, 1), expected_outcome="totally not meeting criteria."
            ),
            Rubric(
                score_range=(2, 3),
                expected_outcome="barely meeting criteria only in a few parts of output.",
            ),
            Rubric(
                score_range=(4, 5),
                expected_outcome="barely meeting criteria most parts of output.",
            ),
            Rubric(
                score_range=(6, 7),
                expected_outcome="mostly meeting criteria but missing a lot of minor details.",
            ),
            Rubric(
                score_range=(8, 9),
                expected_outcome="mostly meeting criteria but missing a few minor details.",
            ),
            Rubric(
                score_range=(10, 10), expected_outcome="perfectly meeting criteria."
            ),
        ]

    def evaluate(self, test_case: LLMTestCase) -> List[Tuple[str, float, str]]:
        """
        Runs the evaluation on a single test case against all criteria.

        Args:
            test_case (LLMTestCase): The test case to evaluate.

        Returns:
            List[Tuple[str, float, str]]: A list of tuples, where each tuple
                                          contains the criterion name, its score, and the reasoning.
        """
        results = []
        criteria_intro = "You are a maintenance knowledge expert in the engineering industry. Evaluate the output and assign a score from 0–10 for each criterion. Justify your score and make recommendations for improvements."

        for name, criterion_text in self.criteria.items():
            metric = GEval(
                name=f"{name} Evaluator",
                criteria=f"{criteria_intro}\n{criterion_text}",
                evaluation_params=[
                    LLMTestCaseParams.INPUT,
                    LLMTestCaseParams.ACTUAL_OUTPUT,
                    LLMTestCaseParams.EXPECTED_OUTPUT,
                ],
                rubric=self.rubrics,
                verbose_mode=False,
                threshold=0.5,  # higher threshold means stricter evaluator
                model="gpt-4o",  # Force a powerful model for reliable evaluation
            )
            score = None
            reason = ""
            try:
                self.logger.info(f"Evaluating metric: {name}")
                # logger.debug(f"Test Case Input: {test_case.input}")
                # logger.debug(f"Test Case Actual Output: {test_case.actual_output}")
                # logger.debug(f"Test Case Expected Output: {test_case.expected_output}")

                metric.measure(test_case)
                score = metric.score
                reason = metric.reason
                self.logger.debug(f"score: {score}")
                self.logger.debug(f"reason: {reason}")
            except AssertionError as e:
                # This block will now catch assertion errors when the score is below the threshold.
                # The score and reason are not on the metric object, but in the error string.
                error_str = str(e)
                self.logger.warning(
                    f"Metric '{name}' scored below threshold. Parsing error: {error_str}"
                )

                # Use regex to extract the score and reason from the error string
                score_match = re.search(r"score\s*[:=]\s*(\d+(\.\d+)?)(?:\s*/\s*10|\s*out of\s*10)?", error_str, re.IGNORECASE)
                reason_match = re.search(r"reason: (.*)", error_str, re.DOTALL)

                score = float(score_match.group(1)) if score_match else None
                reason = (
                    reason_match.group(1).strip()
                    if reason_match
                    else "Reason could not be parsed from error."
                )
            except Exception as e:
                # Catch any other exception during the evaluation, log it, and format it for the UI
                self.logger.error(
                    f"An unexpected error occurred during evaluation for metric '{name}': {e}",
                    exc_info=True,
                )
                score = None  # Explicitly set score to None on failure
                reason = f"**Evaluation failed for metric '{name}'**\n\n**Error:**\n```\n{e}\n```"

            results.append((name, score, reason))

        return results

    def run_full_evaluation(
        self,
        test_case: LLMTestCase,
        contexts: List[str],
        run_deepeval: bool = True,
        run_ragas: bool = True,
    ) -> dict:
        """
        Runs a full evaluation using both DeepEval and RAGAS.
        This is a synchronous wrapper around the async evaluation methods.
        """
        results = {}

        # Run DeepEval evaluation
        if run_deepeval:
            # Note: The 'evaluate' method is synchronous.
            # The results are formatted into a dictionary with a consistent structure.
            deepeval_results = self.evaluate(test_case)
            for name, score, reason in deepeval_results:
                results[name] = {"score": score, "reason": reason}

        # Run RAGAS evaluation
        if run_ragas:
            ragas_dataset = {
                "question": [test_case.input],
                "answer": [test_case.actual_output],
                "contexts": [contexts],
                "ground_truth": [test_case.expected_output],
            }
            ragas_scores = self.evaluate_with_ragas(**ragas_dataset)
            # Format RAGAS scores to match the DeepEval structure for consistency.
            for name, score in ragas_scores.items():
                results[name] = {"score": score, "reason": "N/A (RAGAS metric)"}

        return results

    def evaluate_with_ragas(
        self,
        question: List[str],
        answer: List[str],
        contexts: List[List[str]],
        ground_truth: List[str],
    ) -> dict:
        """
        Evaluates the RAG pipeline performance using RAGAS.

        Args:
            question (List[str]): User queries.
            answer (List[str]): LLM-generated answers.
            contexts (List[List[str]]): List of context strings per query.
            ground_truth (List[str]): Reference (ground truth) answers.

        Returns:
            dict: A dictionary of RAGAS metric scores.
        """
        dataset = Dataset.from_dict(
            {
                "question": question,
                "answer": answer,
                "contexts": contexts,
                "ground_truth": ground_truth,
            }
        )

        # List of metrics to run
        metrics_to_run = [faithfulness, answer_relevancy, context_precision, context_recall, answer_correctness, answer_similarity]
        llm = ChatOpenAI(model="gpt-4o")
        evaluator_llm = LangchainLLMWrapper(llm)

        # Compute the metrics
        results_dataset = ragas_evaluate(dataset=dataset, metrics=metrics_to_run, llm=evaluator_llm)
        self.logger.info("RAGAS evaluation completed.")
        self.logger.info(f"RAGAS evaluation result (type: {type(results_dataset)}):")
        self.logger.info(results_dataset)
        print(results_dataset)
        
        # The output of ragas_evaluate can vary. Using to_pandas() is a robust way
        # to get the results into a standard format.
        try:
            results_df = results_dataset.to_pandas()
        except Exception as e:
            self.logger.error(f"Could not convert ragas result to DataFrame: {e}")
            return {}

        self.logger.info("RAGAS result converted to DataFrame:")
        self.logger.info(results_df.to_string())
        print(results_df.iloc[0])  # Print the first row for debugging

        # Extract the scores from the DataFrame.
        # The DataFrame will have one row corresponding to our single test case.
        if results_df.empty:
            return {}

        scores = {}
        first_row = results_df.iloc[0]
        print(first_row)
        for m in metrics_to_run:
            if m.name in first_row:
                scores[m.name] = first_row[m.name]

        self.logger.info(f"Extracted RAGAS scores: {scores}")
        return scores
