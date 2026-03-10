"use client";

import { createTheme, alpha } from "@mui/material/styles";

// Design Tokens - UI設計仕様書 4.1準拠（ライトテーマ）
const tokens = {
  colors: {
    primary: "#3b82f6",
    primaryLight: "#60a5fa",
    primaryDark: "#2563eb",
    error: "#ef4444",
    success: "#22c55e",
    warning: "#f59e0b",
    background: "#ffffff",
    surface: "#f8fafc",
    surfaceLight: "#f1f5f9",
    text: "#0f172a",
    muted: "#64748b",
    border: "#e2e8f0",
  },
  shape: {
    borderRadius: 12,
  },
};

export const theme = createTheme({
  // 4.1 palette
  palette: {
    mode: "light",
    primary: {
      main: tokens.colors.primary,
      light: tokens.colors.primaryLight,
      dark: tokens.colors.primaryDark,
      contrastText: "#ffffff",
    },
    secondary: {
      main: tokens.colors.muted,
    },
    error: {
      main: tokens.colors.error,
    },
    success: {
      main: tokens.colors.success,
    },
    warning: {
      main: tokens.colors.warning,
    },
    background: {
      default: tokens.colors.background,
      paper: tokens.colors.surface,
    },
    text: {
      primary: tokens.colors.text,
      secondary: tokens.colors.muted,
    },
    divider: tokens.colors.border,
  },

  // 4.1 typography
  typography: {
    fontFamily: '"Space Grotesk", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    h1: {
      fontSize: "clamp(28px, 4vw, 40px)",
      fontWeight: 700,
      lineHeight: 1.2,
      letterSpacing: "-0.01em",
      color: tokens.colors.text,
    },
    h2: {
      fontSize: "clamp(24px, 3vw, 32px)",
      fontWeight: 700,
      lineHeight: 1.3,
    },
    h3: {
      fontSize: "1.25rem",
      fontWeight: 600,
      lineHeight: 1.4,
    },
    h4: {
      fontSize: "1rem",
      fontWeight: 600,
      lineHeight: 1.4,
    },
    body1: {
      fontSize: "1rem",
      lineHeight: 1.6,
    },
    body2: {
      fontSize: "0.875rem",
      lineHeight: 1.5,
    },
    caption: {
      fontSize: "0.75rem",
      lineHeight: 1.4,
      color: tokens.colors.muted,
    },
  },

  // 4.1 shape
  shape: {
    borderRadius: tokens.shape.borderRadius,
  },

  // 4.2 components - defaultProps / styleOverrides / variants
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: tokens.colors.background,
          minHeight: "100vh",
          colorScheme: "light",
        },
        "::-webkit-scrollbar": {
          width: "10px",
        },
        "::-webkit-scrollbar-thumb": {
          background: tokens.colors.border,
          borderRadius: "999px",
        },
        "::-webkit-scrollbar-track": {
          background: "transparent",
        },
      },
    },

    MuiButton: {
      defaultProps: {
        disableElevation: true,
        variant: "contained",
      },
      styleOverrides: {
        root: {
          textTransform: "none",
          fontWeight: 600,
          borderRadius: tokens.shape.borderRadius,
          padding: "10px 20px",
        },
        contained: {
          backgroundColor: tokens.colors.primary,
          color: "#ffffff",
          "&:hover": {
            backgroundColor: tokens.colors.primaryDark,
            boxShadow: `0 4px 12px ${alpha(tokens.colors.primary, 0.3)}`,
          },
          "&:disabled": {
            backgroundColor: tokens.colors.border,
            color: tokens.colors.muted,
          },
        },
      },
    },

    MuiTextField: {
      defaultProps: {
        size: "small",
        variant: "outlined",
        fullWidth: true,
      },
      styleOverrides: {
        root: {
          "& .MuiOutlinedInput-root": {
            borderRadius: tokens.shape.borderRadius,
            backgroundColor: tokens.colors.background,
            "& fieldset": {
              borderColor: tokens.colors.border,
            },
            "&:hover fieldset": {
              borderColor: tokens.colors.muted,
            },
            "&.Mui-focused fieldset": {
              borderColor: tokens.colors.primary,
            },
          },
        },
      },
    },

    MuiSelect: {
      defaultProps: {
        size: "small",
        variant: "outlined",
      },
      styleOverrides: {
        root: {
          borderRadius: tokens.shape.borderRadius,
          backgroundColor: tokens.colors.background,
        },
      },
    },

    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: "none",
          backgroundColor: tokens.colors.surface,
          border: `1px solid ${tokens.colors.border}`,
        },
      },
    },

    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          backgroundColor: tokens.colors.surface,
          border: `1px solid ${tokens.colors.border}`,
          boxShadow: "0 1px 3px rgba(0, 0, 0, 0.08), 0 4px 12px rgba(0, 0, 0, 0.05)",
        },
      },
    },

    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          fontWeight: 600,
        },
        filled: {
          backgroundColor: tokens.colors.surfaceLight,
          color: tokens.colors.text,
        },
        outlined: {
          borderColor: tokens.colors.primary,
          color: tokens.colors.primary,
        },
      },
    },

    MuiCheckbox: {
      defaultProps: {
        color: "primary",
      },
    },

    MuiFormControlLabel: {
      styleOverrides: {
        root: {
          marginLeft: 0,
        },
      },
    },
  },
});

export default theme;
