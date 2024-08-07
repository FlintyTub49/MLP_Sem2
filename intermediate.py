import time
import random
import tqdm
import matplotlib.pyplot as plt

from utility.special_utils import *
from utility.noise_functions import *
import torch
import torch.nn as nn
import torch.optim as optim
import torchvision.transforms.functional as TF
from torchvision import utils

from models.AutoEncShallow import *
from models.SkiDwithSkipUnet import *
from models.SuperMRI import *

import warnings
warnings.filterwarnings("ignore")


# Initialize the autoencoder
model = UNet(use_attention_gate=True)
# model.load_state_dict(torch.load('final/Unet_3.pth'))

data_dir = 'data/'
batch_size = 32
mid_train_loader, mid_val_loader, mid_test_loader = loadData('intermediate_data/Skid_MSE', batch_size, test_size=0.2, color='gray', noise=False)
mid_train_original, mid_val_original, mid_test_original = loadData('intermediate_data/Skid_MSE_og2', batch_size, test_size=0.2, color='gray', noise=False)
print('Data Loading Complete!')
# showImages(mid_train_loader, 5)
# showImages(mid_train_original, 5)

# ------------------------ Move the model to GPU ------------------------ #
device = torch.device('mps' if torch.backends.mps.is_available() else 'cpu')
print(f'Device: {device}\n')
model.to(device)

# Define the loss function and optimizer
criterion = nn.MSELoss() ##nn.functional.binary_cross_entropy_with_logits
optimizer = optim.Adam(model.parameters(), lr=0.001)

# Train Model
check_loss = 999
to_train = 0
num_epochs = 50
if to_train:
	for epoch in range(num_epochs):
		start = time.time()
		for i, (real, mod) in enumerate(tqdm.tqdm(zip(mid_train_original, mid_train_loader), total=len(mid_train_original))):
			actual, _ = real
			_, modif = mod
			optimizer.zero_grad()

			output = model(modif)
			loss = criterion(output, actual)

			loss.backward()
			optimizer.step()

		if loss.item() < check_loss:
			check_loss = loss.item()
			print(f'Saving New Best Model')
			torch.save(model.state_dict(), 'saved_models/Unet_3.pth')

		print(f'Time taken for epoch: {time.time() - start}')
		print(f'Epoch [{epoch + 1}/{num_epochs}]  |  Loss: {loss.item()}\n')
		
# Load the model and test the autoencoder on test set
model = UNet(use_attention_gate=True)
model.load_state_dict(torch.load('saved_models/Unet_3.pth'))
model.to(device)
print('Model Loaded\n')

# Evaluate the model
print(f'Evaluating the Model:')
test_loss = evaluate_model_pipeline(model, mid_test_original, mid_test_loader, device)
print(f'Test loss: {test_loss}\n')

# PSNR of Model
print(f'Calculating PSNR of Model:')
psnr = PSNR_pipeline(model, mid_test_original, mid_test_loader, device)
print(f'PSNR on Test: {psnr}\n')

# SSIM of Model
print(f'Calculating SSIM of Model:')
psnr = SSIM_pipeline(model, mid_test_original, mid_test_loader, device)
print(f'SSIM on Test: {psnr}\n')

# Generate output for random images
n = 5
output_images = generate_images_pipeline(model, mid_test_original, mid_test_loader, n, device, path='experiment/bUnet_big-MSE')
print('Images Generated')