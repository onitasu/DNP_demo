"use client";

import { FormEvent, useState } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Container,
  FormControlLabel,
  Stack,
  Typography,
} from "@mui/material";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import { PageHeader, FormRow, ResultCard, InfoRow, StatusChip } from "@/ui";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8002";

type TranscriptionResult = {
  full_text: string;
  document_type?: string | null;
};

type ReceiptInfo = {
  store_name?: string | null;
  store_address?: string | null;
  store_phone?: string | null;
  total_amount?: string | null;
  tax_rate?: string | null;
  tax_amount?: string | null;
  subtotal_amount?: string | null;
  issue_date?: string | null;
  issue_time?: string | null;
  receipt_number?: string | null;
  invoice_number?: string | null;
  payment_method?: string | null;
  items_summary?: string | null;
};

type OCRResponse = {
  provider: string;
  model: string;
  transcription: TranscriptionResult;
  receipt_info: ReceiptInfo;
  calculated_receipt_info: ReceiptInfo;
  duration_ms: number;
};

type Status = "idle" | "uploading" | "processing" | "error" | "done";

export default function HomePage() {
  const [file, setFile] = useState<File | null>(null);
  const [calculate, setCalculate] = useState(true);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<OCRResponse | null>(null);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setResult(null);

    if (!file) {
      setError("ファイルを選択してください");
      setStatus("error");
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setError("ファイルサイズは10MB以下にしてください");
      setStatus("error");
      return;
    }

    setStatus("processing");
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("calculate_missing", calculate ? "true" : "false");

      const res = await fetch(`${API_BASE}/api/ocr`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const message = await res.text();
        throw new Error(message || "OCRに失敗しました");
      }

      const data: OCRResponse = await res.json();
      setResult(data);
      setStatus("done");
    } catch (err) {
      const message = err instanceof Error ? err.message : "エラーが発生しました";
      setError(message);
      setStatus("error");
    }
  };

  return (
    <Container maxWidth="lg" sx={{ py: 6 }}>
      <PageHeader
        title="AI-OCR demo"
      />

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
          gap: 2,
          alignItems: "flex-start",
        }}
      >
        {/* Upload Form Panel */}
        <Box>
          <Card>
            <CardContent component="form" onSubmit={handleSubmit} sx={{ p: 3 }}>
              <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1.5 }}>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    ステップ1
                  </Typography>
                  <Typography variant="h3">ファイルをアップロード</Typography>
                </Box>
                <StatusChip label={status === "processing" ? "処理中" : "待機中"} active={status === "processing"} />
              </Box>

              <FormRow label="ファイル" help="対応: JPG, PNG, GIF, BMP, WebP, PDF（10MBまで）">
                <Box
                  sx={{
                    border: "1px dashed",
                    borderColor: "divider",
                    borderRadius: 1.5,
                    p: 1.5,
                    bgcolor: "background.default",
                  }}
                >
                  <input
                    type="file"
                    accept="image/*,application/pdf"
                    onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                    style={{ width: "100%" }}
                  />
                </Box>
              </FormRow>

              <FormControlLabel
                control={<Checkbox checked={calculate} onChange={(e) => setCalculate(e.target.checked)} />}
                label="消費税と税抜金額を自動補完する"
                sx={{ mb: 2 }}
              />

              <Stack direction="row" spacing={1.5} alignItems="center">
                <Button type="submit" disabled={status === "processing"} startIcon={<CloudUploadIcon />}>
                  {status === "processing" ? "解析中..." : "アップロードして解析"}
                </Button>
                {error && (
                  <Typography color="error" fontWeight={600}>
                    {error}
                  </Typography>
                )}
              </Stack>
            </CardContent>
          </Card>
        </Box>

        {/* Result Panel */}
        <Box>
          <Card sx={{ minHeight: 400 }}>
            <CardContent sx={{ p: 3 }}>
              <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1.5 }}>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    ステップ2
                  </Typography>
                  <Typography variant="h3">結果ビュー</Typography>
                </Box>
                {result ? (
                  <StatusChip label={`${result.provider.toUpperCase()} · ${result.model} · ${result.duration_ms} ms`} active />
                ) : (
                  <StatusChip label="結果待ち" />
                )}
              </Box>

              {!result && (
                <Box
                  sx={{
                    p: 2.5,
                    border: "1px dashed",
                    borderColor: "divider",
                    borderRadius: 1.5,
                    color: "text.secondary",
                  }}
                >
                  <Typography>アップロード後に抽出結果がここに表示されます。</Typography>
                  <Typography variant="caption" color="text.secondary">
                    構造化JSONも確認できます。
                  </Typography>
                </Box>
              )}

              {result && (
                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: { xs: "1fr", sm: "repeat(auto-fit, minmax(240px, 1fr))" },
                    gap: 1.5,
                  }}
                >
                  <ResultCard title="店舗情報">
                    <InfoRow label="店舗名" value={result.calculated_receipt_info.store_name} />
                    <InfoRow label="住所" value={result.calculated_receipt_info.store_address} />
                    <InfoRow label="電話" value={result.calculated_receipt_info.store_phone} />
                    <InfoRow label="発行日" value={result.calculated_receipt_info.issue_date} />
                    <InfoRow label="発行時刻" value={result.calculated_receipt_info.issue_time} />
                  </ResultCard>

                  <ResultCard title="金額">
                    <InfoRow label="合計" value={result.calculated_receipt_info.total_amount} strong />
                    <InfoRow label="税率" value={result.calculated_receipt_info.tax_rate} />
                    <InfoRow label="消費税" value={result.calculated_receipt_info.tax_amount} />
                    <InfoRow label="税抜" value={result.calculated_receipt_info.subtotal_amount} />
                    <InfoRow label="支払方法" value={result.calculated_receipt_info.payment_method} />
                  </ResultCard>

                  <ResultCard title="識別情報">
                    <InfoRow label="レシート番号" value={result.calculated_receipt_info.receipt_number} />
                    <InfoRow label="インボイス番号" value={result.calculated_receipt_info.invoice_number} />
                    <InfoRow label="商品概要" value={result.calculated_receipt_info.items_summary} />
                  </ResultCard>

                  <ResultCard title="全文テキスト" wide>
                    <Box
                      component="pre"
                      sx={{
                        bgcolor: "background.default",
                        color: "text.secondary",
                        p: 1.5,
                        borderRadius: 1.5,
                        border: "1px solid",
                        borderColor: "divider",
                        whiteSpace: "pre-wrap",
                        maxHeight: 240,
                        overflow: "auto",
                        fontFamily: "monospace",
                        fontSize: 12,
                        m: 0,
                      }}
                    >
                      {result.transcription.full_text || "(空)"}
                    </Box>
                  </ResultCard>

                  <ResultCard title="Raw JSON" wide>
                    <Box
                      component="pre"
                      sx={{
                        bgcolor: "background.default",
                        color: "text.secondary",
                        p: 1.5,
                        borderRadius: 1.5,
                        border: "1px solid",
                        borderColor: "divider",
                        whiteSpace: "pre-wrap",
                        maxHeight: 240,
                        overflow: "auto",
                        fontFamily: "monospace",
                        fontSize: 12,
                        m: 0,
                      }}
                    >
                      {JSON.stringify(result, null, 2)}
                    </Box>
                  </ResultCard>
                </Box>
              )}
            </CardContent>
          </Card>
        </Box>
      </Box>
    </Container>
  );
}
