import time
import random
import tqdm
import matplotlib.pyplot as plt

import torch
import torch.nn as nn
import torch.optim as optim
import torchvision.transforms.functional as TF

from utils import *
from AutoEncShallow import *
from SkiD import *
from SkiDwithSkip import *

# Initialize the autoencoder
model = SkiDFCN()

data_dir = 'data/'
batch_size = 8
train_loader, test_loader = loadData(data_dir, batch_size, test_size=0.01, color='gray', noise=True)
print('Data Loading Complete!')
# showImages(train_loader, 5)

# Move the model to GPU
device = torch.device('mps' if torch.backends.mps.is_available() else 'cpu')
print(f'Device: {device}')
model.to(device)

# Define the loss function and optimizer
criterion = nn.MSELoss()
optimizer = optim.Adam(model.parameters(), lr=0.01)

# Training the autoencoder
to_train = 0
num_epochs = 1
if to_train:
	start = time.time()
	for epoch in range(num_epochs):
		for i, data in enumerate(tqdm.tqdm(train_loader)):
			img, _ = data
			optimizer.zero_grad()
			output = model(img)
			loss = criterion(output, img)
			loss.backward()
			optimizer.step()

		print(f'Time for one epoch: {time.time() - start}')
		print('Epoch [{}/{}], Loss: {:.4f}'.format(epoch+1, num_epochs, loss.item()))

	# Save the model
	torch.save(model.state_dict(), 'SkidFCN.pth')

# Load the model and test the autoencoder on test set
model = AutoencoderWithoutSkip()
model.load_state_dict(torch.load('conv_autoencoder_without.pth'))
# model = SkiDFCN()
# model.load_state_dict(torch.load('SkidFCN.pth'))
model.to(device)
print('Model Loaded')

# Evaluate the model
# test_loss = model.evaluate_model(model, test_loader, device)
# print(f'Test loss: {test_loss:.4f}')

# Generate output for random images
n = 4
# output_images = model.generate_images(model, test_loader, n, device)
# print('Images Generated')

# Create specific output images
input_image = next(iter(test_loader))[0][7]
model.create_output(model, input_image, device)