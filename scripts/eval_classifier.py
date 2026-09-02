"""
Evaluation harness for the Hybrid LLM Classifier.
Generates 50 synthetic examples and tests predictions against ground truth.
Createsdocs/classifier_eval_results.md
"""

import sys
import os
import random
from collections import defaultdict

# Add root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.data_generator import RAW_FAILURE_TEXTS
from app.services.llm_classifier import classify, VALID_CATEGORIES

def run_evaluation():
    print("Starting evaluation harness with 50 examples...")
    
    # 1. Generate 50 labeled examples
    test_cases = []
    # Seed for reproducibility
    random.seed(42)
    
    categories = [cat for cat in RAW_FAILURE_TEXTS.keys()]
    
    for i in range(50):
        true_cat = random.choice(categories)
        raw_text = random.choice(RAW_FAILURE_TEXTS[true_cat])
        test_cases.append((raw_text, true_cat))
        
    # 2. Run through LLM classifier
    results = []
    correct_count = 0
    
    llm_total = 0
    llm_correct = 0
    fallback_total = 0
    fallback_correct = 0

    # Confusion matrix tracker: conf_matrix[true][predicted] = count
    conf_matrix = defaultdict(lambda: defaultdict(int))
    # Correct/Incorrect confidence tracking
    correct_confidences = []
    incorrect_confidences = []
    
    # Precision / Recall stats
    # For each category: TP, FP, FN
    stats = {cat: {"tp": 0, "fp": 0, "fn": 0} for cat in VALID_CATEGORIES}
    
    for idx, (raw_text, true_cat) in enumerate(test_cases):
        print(f"[{idx+1}/50] Testing: '{raw_text}' -> True: {true_cat}")
        res = classify(raw_text, fallback_code=true_cat)
        predicted_cat = res["diagnosis"]
        confidence = res["confidence"]
        mode_used = res.get("mode_used", "deterministic_fallback")
        
        conf_matrix[true_cat][predicted_cat] += 1
        
        is_correct = (predicted_cat == true_cat)
        if is_correct:
            correct_count += 1
            correct_confidences.append(confidence)
            stats[true_cat]["tp"] += 1
        else:
            incorrect_confidences.append(confidence)
            stats[true_cat]["fn"] += 1
            stats[predicted_cat]["fp"] += 1
            
        if mode_used == "llm":
            llm_total += 1
            if is_correct:
                llm_correct += 1
        else:
            fallback_total += 1
            if is_correct:
                fallback_correct += 1

        results.append({
            "raw_text": raw_text,
            "true_cat": true_cat,
            "pred_cat": predicted_cat,
            "confidence": confidence,
            "mode_used": mode_used,
            "correct": is_correct,
            "reasoning": res.get("reasoning", "")
        })
        
    overall_accuracy = correct_count / 50.0
    llm_accuracy = llm_correct / llm_total if llm_total > 0 else 0.0
    fallback_accuracy = fallback_correct / fallback_total if fallback_total > 0 else 0.0

    avg_correct_conf = sum(correct_confidences) / len(correct_confidences) if correct_confidences else 0.0
    avg_incorrect_conf = sum(incorrect_confidences) / len(incorrect_confidences) if incorrect_confidences else 0.0
    
    # Generate Confusion Matrix Table
    cat_list = sorted(list(VALID_CATEGORIES))
    headers = ["True \\ Pred"] + cat_list
    cm_rows = []
    for true_cat in cat_list:
        row = [true_cat]
        for pred_cat in cat_list:
            row.append(str(conf_matrix[true_cat][pred_cat]))
        cm_rows.append(row)
        
    # Generate Precision / Recall Table
    pr_rows = []
    for cat in cat_list:
        tp = stats[cat]["tp"]
        fp = stats[cat]["fp"]
        fn = stats[cat]["fn"]
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        
        pr_rows.append([
            cat,
            f"{precision:.2f}",
            f"{recall:.2f}",
            str(tp),
            str(fp),
            str(fn)
        ])
        
    # Build markdown report
    report = []
    report.append("# LLM Classifier Evaluation Results\n")
    report.append("### Summary Metrics\n")
    report.append(f"- **Overall Accuracy**: {overall_accuracy * 100:.1f}% ({correct_count}/50)\n")
    report.append(f"- **LLM-Only Accuracy**: {llm_accuracy * 100:.1f}% ({llm_correct}/{llm_total})\n")
    report.append(f"- **Deterministic Fallback Accuracy**: {fallback_accuracy * 100:.1f}% ({fallback_correct}/{fallback_total})\n")
    report.append(f"- **Average Confidence (Correct)**: {avg_correct_conf:.2f}\n")
    report.append(f"- **Average Confidence (Incorrect)**: {avg_incorrect_conf:.2f}\n")
    report.append("\n### Precision and Recall per Category\n")
    report.append("| Category | Precision | Recall | True Positives (TP) | False Positives (FP) | False Negatives (FN) |\n")
    report.append("| --- | --- | --- | --- | --- | --- |\n")
    for r in pr_rows:
        report.append(f"| {' | '.join(r)} |\n")
        
    report.append("\n### Confusion Matrix\n")
    report.append(f"| {' | '.join(headers)} |\n")
    report.append(f"| {' | '.join(['---'] * len(headers))} |\n")
    for r in cm_rows:
        report.append(f"| {' | '.join(r)} |\n")
        
    report.append("\n### Detail Log\n")
    report.append("| Raw Text | True Category | Predicted Category | Confidence | Mode Used | Correct? | Reasoning |\n")
    report.append("| --- | --- | --- | --- | --- | --- | --- |\n")
    for r in results:
        clean_text = r['raw_text'].replace('|', '\\|')
        clean_reason = r['reasoning'].replace('|', '\\|').replace('\n', ' ')
        report.append(f"| {clean_text} | {r['true_cat']} | {r['pred_cat']} | {r['confidence']:.2f} | {r['mode_used']} | {'Yes' if r['correct'] else 'No'} | {clean_reason} |\n")
        
    # Write to docs/classifier_eval_results.md
    os.makedirs("docs", exist_ok=True)
    with open("docs/classifier_eval_results.md", "w", encoding="utf-8") as f:
        f.writelines(report)
        
    print("\n--- RESULTS SUMMARY ---")
    print(f"Overall Accuracy: {overall_accuracy * 100:.1f}% ({correct_count}/50)")
    print(f"LLM-Only Accuracy: {llm_accuracy * 100:.1f}% ({llm_correct}/{llm_total})")
    print(f"Deterministic Fallback Accuracy: {fallback_accuracy * 100:.1f}% ({fallback_correct}/{fallback_total})")
    print(f"Avg Correct Confidence: {avg_correct_conf:.2f}")
    print(f"Avg Incorrect Confidence: {avg_incorrect_conf:.2f}")
    print("Report successfully saved to docs/classifier_eval_results.md")
    
if __name__ == "__main__":
    run_evaluation()
