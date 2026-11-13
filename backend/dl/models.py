"""Small device-agnostic trajectory architectures."""

from typing import Literal, cast

import torch
from torch import nn

ModelKind = Literal["lstm", "gru", "transformer"]


class RecurrentTrajectoryModel(nn.Module):
    def __init__(
        self,
        *,
        kind: Literal["lstm", "gru"],
        input_size: int,
        hidden_size: int,
        output_size: int,
        dropout: float,
    ) -> None:
        super().__init__()
        recurrent = nn.LSTM if kind == "lstm" else nn.GRU
        self.encoder = recurrent(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=2,
            batch_first=True,
            dropout=dropout,
        )
        self.head = nn.Sequential(
            nn.LayerNorm(hidden_size),
            nn.Linear(hidden_size, hidden_size),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, output_size),
        )

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        encoded, _state = self.encoder(values)
        return cast(torch.Tensor, self.head(encoded[:, -1, :]))


class TransformerTrajectoryModel(nn.Module):
    def __init__(
        self,
        *,
        input_size: int,
        hidden_size: int,
        output_size: int,
        dropout: float,
        sequence_length: int,
    ) -> None:
        super().__init__()
        self.input_projection = nn.Linear(input_size, hidden_size)
        self.position = nn.Parameter(torch.zeros(1, sequence_length, hidden_size))
        layer = nn.TransformerEncoderLayer(
            d_model=hidden_size,
            nhead=4,
            dim_feedforward=hidden_size * 2,
            dropout=dropout,
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(layer, num_layers=2, enable_nested_tensor=False)
        self.head = nn.Sequential(
            nn.LayerNorm(hidden_size),
            nn.Linear(hidden_size, output_size),
        )
        nn.init.normal_(self.position, std=0.02)

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        projected = self.input_projection(values) + self.position[:, : values.shape[1], :]
        encoded = self.encoder(projected)
        return cast(torch.Tensor, self.head(encoded[:, -1, :]))


def create_model(
    kind: ModelKind,
    *,
    input_size: int,
    hidden_size: int,
    output_size: int,
    dropout: float,
    sequence_length: int,
) -> nn.Module:
    if kind in ("lstm", "gru"):
        return RecurrentTrajectoryModel(
            kind=kind,
            input_size=input_size,
            hidden_size=hidden_size,
            output_size=output_size,
            dropout=dropout,
        )
    return TransformerTrajectoryModel(
        input_size=input_size,
        hidden_size=hidden_size,
        output_size=output_size,
        dropout=dropout,
        sequence_length=sequence_length,
    )
