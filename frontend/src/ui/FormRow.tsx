"use client";

import { FormControl, FormHelperText, FormLabel, Stack } from "@mui/material";
import { ReactNode } from "react";

type Props = {
  label: string;
  required?: boolean;
  error?: string;
  help?: string;
  children: ReactNode;
};

export function FormRow({ label, required, error, help, children }: Props) {
  return (
    <FormControl fullWidth error={!!error} sx={{ mb: 2 }}>
      <FormLabel required={required} sx={{ mb: 0.75, fontWeight: 500 }}>
        {label}
      </FormLabel>
      <Stack spacing={0.5}>
        {children}
        {(error || help) && (
          <FormHelperText error={!!error} sx={{ mx: 0 }}>
            {error || help}
          </FormHelperText>
        )}
      </Stack>
    </FormControl>
  );
}
