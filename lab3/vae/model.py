from enum import Enum, auto
import torch
from torch import nn
from torch import Tensor
import torch.nn.functional as F
from model_utils.base.config import BaseConfig


class D(Enum):
    CIFAR = auto()
    NMINST = auto()

INPUT_SHAPE = {
    D.CIFAR: (32, 3),
    D.NMINST: (28, 1),
}

class ModelConfig(BaseConfig):
    latent_dims: int = 2 
    capacity: int = 64
    variational_beta: int = 1
    input_shape = INPUT_SHAPE[D.NMINST]

class Encoder(nn.Module):
    def __init__(self, config: ModelConfig):
        super().__init__()
        c = config.capacity * config.input_shape[-1]
        # input: 1 x w x h
        self.conv1 = nn.Conv2d(config.input_shape[-1], c, kernel_size=4, stride=2, padding=1)
        # out: 1 x w/2 x h/2
        self.conv2 = nn.Conv2d(c, c*2, kernel_size=4, stride=2, padding=1)
        # out: c*2 x w/4 x h/4
        dim = c * 2 * (config.input_shape[0] // 4) ** 2
        self.fc = nn.Linear(dim, dim / 2)
        self.fc_mu = nn.Linear(dim / 2, config.latent_dims)
        self.fc_logvar = nn.Linear(dim / 2, config.latent_dims)
            
    def forward(self, x: Tensor):
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))

        # flatten batch of multi-channel feature maps to a batch of feature vectors
        x = x.reshape(x.size(0), -1)
        x = F.relu(self.fc(x))
        x_mu = self.fc_mu(x)
        x_logvar = self.fc_logvar(x)
        return x_mu, x_logvar

class Decoder(nn.Module):
    def __init__(self, config: ModelConfig):
        super().__init__()
        self.config = config
        c = config.capacity * config.input_shape[-1]
        dim = c * 2 * (config.input_shape[0] // 4) ** 2
        self.fc = nn.Sequential(
            nn.Linear(config.latent_dims, dim / 2),
            nn.ReLU(inplace=True),
            nn.Linear(dim / 2, dim),
            nn.ReLU(inplace=True),
        )
        self.conv2 = nn.ConvTranspose2d(c*2, c, kernel_size=4, stride=2, padding=1)
        self.conv1 = nn.ConvTranspose2d(c, config.input_shape[-1],
                                        kernel_size=4, stride=2, padding=1)
            
    def forward(self, x: Tensor):
        x = self.fc(x)
        dim = self.config.input_shape[0] // 4
        c = self.config.capacity * 2 * self.config.input_shape[-1]
        x = x.view(x.size(0), c, dim, dim)
        # unflatten batch of feature vectors to a batch of multi-channel feature maps
        x = F.relu(self.conv2(x))
        # last layer before output is sigmoid, since we are using BCE as reconstruction loss
        # x = torch.sigmoid(self.conv1(x))
        x = self.conv1(x)
        # b x c x w x h
        x = torch.softmax(x, dim=1)
        return x
    
class VariationalAutoencoder(nn.Module):
    def __init__(self, config: ModelConfig):
        super().__init__()
        self.encoder = Encoder(config)
        self.decoder = Decoder(config)
        self.config = config
    
    def forward(self, x):
        latent_mu, latent_logvar = self.encoder(x)
        latent = self.latent_sample(latent_mu, latent_logvar)
        x_recon = self.decoder(latent)
        return x_recon, latent_mu, latent_logvar
    
    def latent_sample(self, mu: Tensor, logvar: Tensor):
        if self.training:
            # the reparameterization trick
            std = logvar.mul(0.5).exp_()
            eps = torch.empty_like(std).normal_()
            return eps.mul(std).add_(mu)
        return mu
    
    def criterion(self, x: Tensor, recon_x: Tensor, mu: Tensor, logvar: Tensor):
        # recon_x is the probability of a multivariate Bernoulli distribution p.
        # -log(p(x)) is then the pixel-wise binary cross-entropy.
        # Averaging or not averaging the binary cross-entropy over all pixels here
        # is a subtle detail with big effect on training, since it changes the weight
        # we need to pick for the other loss term by several orders of magnitude.
        # Not averaging is the direct implementation of the negative log likelihood,
        # but averaging makes the weight of the other loss term independent of the image resolution.
        dim = self.config.input_shape[0] ** 2
        recon_loss = F.binary_cross_entropy(recon_x.reshape(-1, dim), x.reshape(-1, dim), reduction='sum')
        #MSEloss
        # KL-divergence between the prior distribution over latent vectors
        # (the one we are going to sample from when generating new images)
        # and the distribution estimated by the generator for the given image.
        kldivergence = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())
        
        return recon_loss + self.config.variational_beta * kldivergence