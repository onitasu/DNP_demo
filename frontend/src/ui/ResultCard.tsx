"use client";

import { Card, CardContent, Typography } from "@mui/material";
import { ReactNode } from "react";

type Props = {
  title: string;
  wide?: boolean;
  children: ReactNode;
};

export function ResultCard({ title, wide, children }: Props) {
  return (
    <Card
      variant="outlined"
      sx={{
        gridColumn: wide ? "1 / -1" : undefined,
        bgcolor: "rgba(255, 255, 255, 0.02)",
      }}
    >
      <CardContent>
        <Typography variant="h4" sx={{ mb: 1.5 }}>
          {title}
        </Typography>
        {children}
      </CardContent>
    </Card>
  );
}
