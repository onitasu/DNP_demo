"use client";

import { Chip } from "@mui/material";

type Props = {
  label: string;
  active?: boolean;
};

export function StatusChip({ label, active }: Props) {
  return (
    <Chip
      label={label}
      size="small"
      variant={active ? "outlined" : "filled"}
      color={active ? "primary" : "default"}
      sx={{
        fontWeight: 600,
        ...(active && {
          color: "text.primary",
        }),
      }}
    />
  );
}
