import datetime
import csv
import os
import huggingface_hub
from huggingface_hub import Repository
import gradio as gr
from datasets import load_dataset, DatasetDict, Dataset, concatenate_datasets




# Define the dataset repository on Hugging Face Hub
HF_DATASET_REPO = "florentgbelidji/alpine-agent-feedback"


# Load or initialize the dataset
try:
    dataset = load_dataset(HF_DATASET_REPO)
except FileNotFoundError:
    # Initialize an empty dataset if it doesn't exist
    dataset = DatasetDict({
        "train": Dataset.from_dict({
            "timestamp": [datetime.datetime.now().isoformat()],
            "user_feedback": ["Initial feedback"],
        })
    })
    dataset.push_to_hub(HF_DATASET_REPO, token=os.getenv("HF_TOKEN"))


def get_feedback_interface():
    with gr.Tab("Feedback Form"):
        feedback_input = gr.Textbox(label="Your Feedback", lines=4, placeholder="Type your feedback here...")
        submit_button = gr.Button("Submit")
        feedback_response = gr.Markdown(label="feedback_response")

        def add_feedback(feedback):
            from datetime import datetime

            # Append feedback to the dataset
            new_data = {
                "timestamp": [datetime.now().isoformat()],
                "user_feedback": [feedback],
            }
            new_entry = Dataset.from_dict(new_data)
            global dataset
            dataset["train"] = concatenate_datasets([dataset["train"], new_entry])

            # Push updated dataset to the Hub
            dataset.push_to_hub(HF_DATASET_REPO)

            return "Thank you for your feedback!"

        submit_button.click(add_feedback, inputs=[feedback_input], outputs=[feedback_response])

