import torch
import typing as t
from torch import nn
from math import floor
import torchinfo


# ----------------------------------------------------------------------- #
#                                 utils.py                                #
# ----------------------------------------------------------------------- #
class Essentials():
    def __init__(self):
        pass

    def cgetattr(self, obj, attr: str):
        """Case-insensitive getattr"""
        for a in dir(obj):
            if a.lower() == attr.lower():
                return getattr(obj, a)


    def activation(self, name: str):
        """return activation layer with given name"""
        name = name.lower()
        if name == "elu":
            return nn.ELU
        elif name in ["leakyrelu", "lrelu", "leaky_relu"]:
            return nn.LeakyReLU
        elif name == "relu":
            return nn.ReLU
        elif name == "sigmoid":
            return nn.Sigmoid
        elif name == "tanh":
            return nn.Tanh
        elif name == "softmax":
            return nn.Softmax
        elif name == "gelu":
            return nn.GELU
        else:
            raise KeyError(f"activation layer {name} not found.")


    def normalization(self, name: str):
        """return normalization layer with given name"""
        name = name.lower()
        if name in ["batchnorm", "batch_norm", "bn"]:
            return nn.BatchNorm2d
        elif name in ["instancenorm", "instance_norm", "in"]:
            return nn.InstanceNorm2d
        else:
            raise KeyError(f"normalization layer {name} not found.")
        
essense = Essentials()


class Reshape(nn.Module):
    """Reshape layer"""

    def __init__(self, target_shape):
        super(Reshape, self).__init__()
        self.target_shape = target_shape

    def forward(self, x):
        return x.view(self.target_shape)


def get_conv_shape(
    height: int,
    width: int,
    kernel_size: t.Union[int, t.Tuple[int, int]],
    stride: t.Union[int, t.Tuple[int, int]] = 1,
    padding: int = 0,
    dilation: int = 1,
) -> tuple[int, int]:
    """calculate Conv layer output shape"""
    if type(kernel_size) == int:
        kernel_size = (kernel_size, kernel_size)
    if type(stride) == int:
        stride = (stride, stride)
    height = floor(
        ((height + (2 * padding) - (dilation * (kernel_size[0] - 1)) - 1) / stride[0])
        + 1
    )
    width = floor(
        ((width + (2 * padding) - (dilation * (kernel_size[1] - 1)) - 1) / stride[1])
        + 1
    )
    return height, width


# ----------------------------------------------------------------------- #
#                                 unet.py                                 #
# ----------------------------------------------------------------------- #
import math
import torch
import torch.nn as nn
import torch.nn.functional as F

class ConvBlock(nn.Module):
    """
    Convolution block consists of 2 blocks of (conv -> norm -> activation )
    """

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        mid_channels: int = None,
        kernel_size: int = 3,
        padding: int = 1,
        bias: bool = False,
        normalization: str = "instancenorm",
        activation: str = "leakyrelu",
        dropout: float = 0.0,
    ):
        super(ConvBlock, self).__init__()
        if not mid_channels:
            mid_channels = out_channels

        self.conv1 = nn.Conv2d(
            in_channels,
            mid_channels,
            kernel_size=kernel_size,
            padding=padding,
            bias=bias,
        )
        self.norm1 = essense.normalization(normalization)(mid_channels)
        self.activation1 = essense.activation(activation)()
        self.dropout1 = nn.Dropout2d(p=dropout)

        self.conv2 = nn.Conv2d(
            mid_channels,
            out_channels,
            kernel_size=kernel_size,
            padding=padding,
            bias=bias,
        )
        self.norm2 = essense.normalization(normalization)(out_channels)
        self.activation2 = essense.activation(activation)()
        self.dropout2 = nn.Dropout2d(p=dropout)

    def forward(self, x):
        outputs = self.conv1(x)
        outputs = self.norm1(outputs)
        outputs = self.activation1(outputs)
        outputs = self.dropout1(outputs)
        outputs = self.conv2(outputs)
        outputs = self.norm2(outputs)
        outputs = self.activation2(outputs)
        outputs = self.dropout2(outputs)
        return outputs


class DownScale(nn.Module):
    """down scale block with max pool followed by convolution block"""

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        normalization: str = "instancenorm",
        activation: str = "lrelu",
        dropout: float = 0.0,
    ):
        super(DownScale, self).__init__()
        self.max_pool = nn.MaxPool2d(kernel_size=2)
        self.conv_block = ConvBlock(
            in_channels=in_channels,
            out_channels=out_channels,
            normalization=normalization,
            activation=activation,
            dropout=dropout,
        )

    def forward(self, x):
        outputs = self.max_pool(x)
        outputs = self.conv_block(outputs)
        return outputs


class AttentionGate(nn.Module):
    """
    Additive Attention Gate
    reference: https://arxiv.org/abs/1804.03999
    """

    def __init__(self, in_channels: int, normalization: str = "instancenorm"):
        super(AttentionGate, self).__init__()

        self.gating_conv = nn.Conv2d(
            in_channels=in_channels, out_channels=in_channels, kernel_size=1
        )
        self.gating_norm = essense.normalization(normalization)(in_channels)

        self.input_conv = nn.Conv2d(
            in_channels=in_channels, out_channels=in_channels, kernel_size=1
        )
        self.input_norm = essense.normalization(normalization)(in_channels)

        self.relu = essense.activation("relu")()
        self.conv = nn.Conv2d(in_channels=in_channels, out_channels=1, kernel_size=1)
        self.norm = essense.normalization(normalization)(1)
        self.sigmoid = essense.activation("sigmoid")()

    def forward(self, inputs: torch.Tensor, shortcut: torch.Tensor):
        g = self.gating_conv(shortcut)
        g = self.gating_norm(g)

        x = self.input_conv(inputs)
        x = self.input_norm(x)

        alpha = torch.add(g, x)
        alpha = self.relu(alpha)
        alpha = self.conv(alpha)
        alpha = self.norm(alpha)
        attention_mask = self.sigmoid(alpha)
        shortcut = torch.mul(attention_mask, shortcut)

        return shortcut


class UpScale(nn.Module):
    """
    up scale block with transpose convolution followed by convolution block
    """

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        normalization: str = "instancenorm",
        activation: str = "lrelu",
        dropout: float = 0.0,
        use_attention_gate: bool = False,
    ):
        super(UpScale, self).__init__()
        self.transpose_conv = nn.ConvTranspose2d(
            in_channels=in_channels,
            out_channels=in_channels // 2,
            kernel_size=2,
            stride=2,
        )
        self.conv_block = ConvBlock(
            in_channels=in_channels,
            out_channels=out_channels,
            normalization=normalization,
            activation=activation,
            dropout=dropout,
        )
        self.padding = None
        self.sigmoid = essense.activation("sigmoid")()

        self.attention_gate = None
        if use_attention_gate:
            self.attention_gate = AttentionGate(
                in_channels=in_channels // 2, normalization=normalization
            )

    def forward(self, x: torch.Tensor, shortcut: torch.Tensor):
        outputs = self.transpose_conv(x)

        if self.padding is None:
            h_diff = shortcut.shape[2] - outputs.shape[2]
            w_diff = shortcut.shape[3] - outputs.shape[3]
            self.padding = [
                w_diff // 2,
                w_diff - (w_diff // 2),
                h_diff // 2,
                h_diff - (h_diff // 2),
            ]
        outputs = F.pad(outputs, pad=self.padding)

        if self.attention_gate is not None:
            shortcut = self.attention_gate(outputs, shortcut)
        outputs = torch.cat([outputs, shortcut], dim=1)

        outputs = self.conv_block(outputs)
        return outputs


class UNet(nn.Module):
    """
    UNet model
    reference: https://github.com/milesial/Pytorch-UNet/tree/master/unet
    """

    def __init__(self, max_blocks: int = 6, use_attention_gate: bool = False):
        """initialize UNet model
        Args:
          args
          max_blocks: the maximum number of down scale blocks
          use_attention_gate: use attention gate in residual connection
        """
        super(UNet, self).__init__()
        in_channels = 1
        out_channels = 1
        num_filters = 3
        normalization = 'instancenorm'
        activation = 'leakyrelu'
        dropout = 0.0

        # calculate the number of down scale blocks s.t. the smallest block output
        # is at least 2x2 in height and width
        num_blocks = 10
        self.filters = [
            num_filters * (2**i) for i in range(min(num_blocks, max_blocks))
        ]

        self.input_block = ConvBlock(
            in_channels=in_channels,
            out_channels=self.filters[0],
            normalization=normalization,
            activation=activation,
            dropout=dropout,
        )

        self.down_blocks = nn.ModuleList(
            [
                DownScale(
                    in_channels=self.filters[i],
                    out_channels=self.filters[i + 1],
                    normalization=normalization,
                    activation=activation,
                    dropout=dropout,
                )
                for i in range(len(self.filters) - 1)
            ]
        )

        self.up_blocks = nn.ModuleList(
            [
                UpScale(
                    in_channels=self.filters[i],
                    out_channels=self.filters[i - 1],
                    normalization=normalization,
                    activation=activation,
                    dropout=dropout,
                    use_attention_gate=use_attention_gate,
                )
                for i in range(len(self.filters) - 1, 0, -1)
            ]
        )

        self.output_conv = nn.Conv2d(
            in_channels=self.filters[0], out_channels=out_channels, kernel_size=1
        )
        self.sigmoid = None
        # if not args.output_logits:
        #     self.sigmoid = activation("sigmoid")()

    def forward(self, x):
        outputs = self.input_block(x)

        shortcuts = [outputs]
        for i in range(len(self.down_blocks)):
            outputs = self.down_blocks[i](outputs)
            shortcuts.append(outputs)

        shortcuts = shortcuts[-2::-1]
        for i in range(len(self.up_blocks)):
            outputs = self.up_blocks[i](outputs, shortcuts[i])

        outputs = self.output_conv(outputs)
        if self.sigmoid is not None:
            outputs = self.sigmoid(outputs)
        return outputs