"use client";

import { Box, Typography } from "@mui/material";

type Props = {
  label: string;
  value?: string | null;
  strong?: boolean;
};

export function InfoRow({ label, value, strong }: Props) {
  return (
    <Box sx={{ display: "flex", justifyContent: "space-between", gap: 1, my: 0.5 }}>
      <Typography variant="body2" color="text.secondary">
        {label}
      </Typography>
      <Typography
        variant="body2"
        sx={{
          fontWeight: 600,
          textAlign: "right",
          color: strong ? "primary.main" : "text.primary",
        }}
      >
        {value || "-"}
      </Typography>
    </Box>
  );
}
