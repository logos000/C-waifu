import torch
from transformers import pipeline

print("PyTorch version:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
print("CUDA device count:", torch.cuda.device_count())

print(":: Loading model...")
generator = pipeline('text-generation', model='model', device=0)  # 使用GPT-2模型进行测试
print("Model device:", generator.model.device)

prompt = "Once upon a time"
result = generator(prompt, max_length=50, num_return_sequences=1)
print(result)
