import time
import random
import tqdm
import matplotlib.pyplot as plt

import torch
import torch.nn as nn
import torch.optim as optim
import torchvision.transforms.functional as TF

from utils import *
from models import *

# Initialize the autoencoder
model = AutoencoderWithoutSkip()

data_dir = 'data/'
batch_size = 16
train_loader, test_loader = loadData(data_dir, batch_size)
print('Data Loading Complete!')

# Move the model to GPU
device = torch.device('mps' if torch.backends.mps.is_available() else 'cpu')
print(f'Device: {device}')
model.to(device)

# Define the loss function and optimizer
criterion = nn.MSELoss()
optimizer = optim.Adam(model.parameters(), lr=0.01)

# Train the autoencoder
to_train = 0
num_epochs = 10
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
	torch.save(model.state_dict(), 'conv_autoencoder_without.pth')

# Load the model and test the autoencoder on test set
model = AutoencoderWithoutSkip()
model.load_state_dict(torch.load('conv_autoencoder_without.pth'))
model.to(device)
print('Data Loaded')

# Evaluate the model
# test_loss = model.evaluate_model(model, test_loader, device)
# print(f'Test loss: {test_loss:.4f}')

# Generate output images
n = 5
output_images = model.generate_images(model, test_loader, n, device)
print('Images Generated')

# Create output images
# input_image = next(iter(test_loader))[0][0]
# model.create_output(model, input_image, device)