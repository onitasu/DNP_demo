"use client";

import { Box, Chip, Stack, Typography } from "@mui/material";
import { ReactNode } from "react";

type Props = {
  badge?: string;
  title: string;
  description?: string;
  action?: ReactNode;
};

export function PageHeader({ badge, title, description, action }: Props) {
  return (
    <Stack spacing={2} sx={{ mb: 3 }}>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 2 }}>
        <Stack spacing={1}>
          {badge && (
            <Chip
              label={badge}
              size="small"
              sx={{
                width: "fit-content",
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                fontSize: 12,
              }}
            />
          )}
          <Typography variant="h1" component="h1">
            {title}
          </Typography>
        </Stack>
        {action && <Box>{action}</Box>}
      </Box>
      {description && (
        <Typography variant="body1" color="text.secondary">
          {description}
        </Typography>
      )}
    </Stack>
  );
}
