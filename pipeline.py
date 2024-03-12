import time
import random
import tqdm
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore")

# from utility.utils import *
from utility.noise_functions import *
from experiment.special_utils import *

import torch
import torch.nn as nn
import torch.optim as optim
import torchvision.transforms.functional as TF
from torchvision import utils

from models.AutoEncShallow import *
from models.SkiD import *
from models.SkiDwithSkip import *
from models.SkiDwithSkipUnet import *
from models.SuperMRI import *


# --------------------------- Reading the Data -------------------------- #
batch_size = 16
train_loader, test_loader = loadData('data', batch_size, test_size=0.05, color='gray', noise=True)
train_original, test_original = loadData('data', batch_size, test_size=0.05, color='gray', noise=False)
print('Data Loading Complete!')
# showImages(train_loader, 5)
# showImages(train_original, 5)


# ------------------------ Move the model to GPU ------------------------ #
device = torch.device('mps' if torch.backends.mps.is_available() else 'cpu')
print(f'Device: {device}\n')

# Initialize the models
model1 = SkidNet()
model1.load_state_dict(torch.load('saved_models/bSkidNet_0.001.pth'))
model1.to(device)

model2 = UNet(use_attention_gate=True)
model2.load_state_dict(torch.load('experiment/bUnet_big-MSE.pth'))
model2.to(device)


# ------------------ Calculating PSNR for the Pipeline ------------------ #
print('Calculating PSNR for the Pipeline:')
total_psnr = 0.0
num_batches = 0
with torch.no_grad():
    for i, (real, mod) in enumerate(tqdm.tqdm(zip(test_original, test_loader), total=len(test_loader))):
        actual, _ = real
        modif, _ = mod
        modif = modif.to(device)

        # Forward Pass
        output = model1(modif)
        output = model2(output)

        actual = (actual * 255).to(torch.uint8).to(device)
        output = (output * 255).to(torch.uint8).to(device)

        if actual.dim() == 3:
            highest = torch.max(actual, dim = (1, 2)).item()
        else: highest = torch.max(actual).item()

        mse = nn.functional.mse_loss(output, actual)
        psnr = 10 * torch.log10((highest ** 2) / mse)
        total_psnr += psnr.item(); num_batches += 1
print(f'Average PSNR: {total_psnr / num_batches:.4f}\n')


# ---------------- Pushing the images through the models ---------------- #
print('Generating images:')
n = 5
original_images, intermediate_images, generated_images, actual_images = [], [], [], []
random_indices = random.sample(range(batch_size), n)

with torch.no_grad():
    for i, (real, mod) in enumerate(tqdm.tqdm(zip(test_original, test_loader), total=len(test_loader))):
        if i in random_indices:
            actual, _ = real
            modif, _ = mod
            modif = modif.to(device)

            # Forward Pass
            output = model1(modif)
            intermediate_images.append(output[0])

            output = model2(output)

            original_images.append(modif[0])
            generated_images.append(output[0])
            actual_images.append(actual[0])

print(f'Sample Images Selected {random_indices}')


# --------------------- Plotting the selected images -------------------- #
fig, axes = plt.subplots(4, n, figsize=(3 * n, 8))
for i in range(n):
    input_image = original_images[i].cpu().squeeze()
    intermediate_image = intermediate_images[i].cpu().squeeze()
    output_image = generated_images[i].cpu().squeeze()
    actual_image = actual_images[i].cpu().squeeze()

    if len(input_image.shape) == 2:
        axes[0, i].imshow(input_image, cmap='gray')
        axes[1, i].imshow(intermediate_image, cmap='gray')
        axes[2, i].imshow(output_image, cmap='gray')
        axes[3, i].imshow(actual_image, cmap='gray')
    else:
        axes[0, i].imshow(input_image.permute(1, 2, 0))
        axes[1, i].imshow(intermediate_image.permute(1, 2, 0))
        axes[2, i].imshow(output_image.permute(1, 2, 0))
        axes[3, i].imshow(actual_image.permute(1, 2, 0))

    axes[0, i].set_title('Input Image'); axes[0, i].axis('off')
    axes[1, i].set_title('Intermediate Image'); axes[1, i].axis('off')
    axes[2, i].set_title('Output Image'); axes[2, i].axis('off')
    axes[3, i].set_title('Actual Image'); axes[3, i].axis('off')

path = None
if path:
    plt.savefig(f'{path}.png')

plt.show()