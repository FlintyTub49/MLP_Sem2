import time
import random
import tqdm
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore")

import sys
sys.path.append('/Users/arthakhouri/Desktop/UoE/MLP Sem II/MLP_Sem2')

from experiment.special_utils import *
from utility.noise_functions import *

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

# Initialize the autoencoder
model = SkidNet()
model.load_state_dict(torch.load('final/new_SkidNet.pth'))

data_dir = 'data/'
batch_size = 32
mid_train_loader, mid_test_loader = loadData('Skid_MSE', batch_size, test_size=0.2, color='gray', noise=False)
mid_train_original, mid_test_original = loadData('Skid_MSE_og', batch_size, test_size=0.2, color='gray', noise=False)
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
to_train = 1
num_epochs = 5
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
			torch.save(model.state_dict(), 'final/new_SkidNet.pth')

		print(f'Time taken for epoch: {time.time() - start}')
		print(f'Epoch [{epoch + 1}/{num_epochs}]  |  Loss: {loss.item()}\n')
		
# Load the model and test the autoencoder on test set
model = SkidNet()
model.load_state_dict(torch.load('final/new_SkidNet.pth'))
model.to(device)
print('Model Loaded\n')

# Evaluate the model
print(f'Evaluating the Model:')
test_loss = evaluate_model_pipeline(model, mid_test_original, mid_test_loader, device)
print(f'Test loss: {test_loss:.4f}\n')

# PSNR of Model
print(f'Calculating PSNR of Model:')
psnr = PSNR_pipeline(model, mid_test_original, mid_test_loader, device)
print(f'PSNR on Test: {psnr:.4f}\n')

# SSIM of Model
print(f'Calculating SSIM of Model:')
psnr = SSIM_pipeline(model, mid_test_original, mid_test_loader, device)
print(f'SSIM on Test: {psnr:.4f}\n')

# Generate output for random images
n = 5
output_images = generate_images_pipeline(model, mid_test_original, mid_test_loader, n, device, path='experiment/bUnet_big-MSE')
print('Images Generated')