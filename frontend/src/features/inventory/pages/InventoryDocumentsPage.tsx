/* eslint-disable @typescript-eslint/no-unused-vars */
import AddIcon from '@mui/icons-material/Add';
import InventoryIcon from '@mui/icons-material/Inventory';
import MoveDownIcon from '@mui/icons-material/MoveDown';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  TextField,
  Toolbar,
  Typography,
} from '@mui/material';
import { useMutation, useQuery } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useMemo, useState } from 'react';

import { listEntities } from '../../organizations/api';
import {
  addDocumentLine,
  cancelDocument,
  createInventory,
  deleteInventory,
  listInventory,
  lowStock,
  postDocument,
} from '../api';
import type {
  Category,
  InventoryDocument,
  Item,
  Location,
  Site,
  StockBalance,
  Unit,
  Warehouse,
} from '../types';
import { queryClient } from '../../../services/queryClient';
import type { ApiError } from '../../../services/apiClient';

import {
  DocumentCreateDialog,
  DocumentTable,
  EmptyState,
  EmptyTable,
  FriendlyError,
  ItemDialog,
  LoadingState,
  MetricCard,
  PageHeader,
  SettingsCrud,
  StateChip,
  StockTable,
  TransferPanel,
  formatQuantity,
  itemTypeLabel,
  nameById,
  totalsByItem,
  unitSymbol,
  useInventoryList,
  useInventoryLookups,
} from './shared';
import type { SettingTab } from './shared';

export function InventoryDocumentsPage() {
  const [createOpen, setCreateOpen] = useState(false);
  const [posting, setPosting] = useState<InventoryDocument | null>(null);
  const [cancelling, setCancelling] = useState<InventoryDocument | null>(null);
  const [cancelReason, setCancelReason] = useState('');
  const lookups = useInventoryLookups();
  const documentsQuery = useInventoryList('documents');
  const postMutation = useMutation({
    mutationFn: (documentId: string) => postDocument(documentId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['inventory'] }),
  });
  const cancelMutation = useMutation({
    mutationFn: ({ documentId, reason }: { documentId: string; reason: string }) =>
      cancelDocument(documentId, reason),
    onSuccess: () => {
      setCancelling(null);
      setCancelReason('');
      return queryClient.invalidateQueries({ queryKey: ['inventory'] });
    },
  });

  return (
    <Stack spacing={3}>
      <PageHeader
        action={
          <Button startIcon={<AddIcon />} variant="contained" onClick={() => setCreateOpen(true)}>
            Створити документ
          </Button>
        }
        subtitle="Чернетки, проведені документи та сторнування."
        title="Складські документи"
      />
      {postMutation.error ? <FriendlyError error={postMutation.error as ApiError} /> : null}
      <Paper variant="outlined">
        {documentsQuery.isLoading || lookups.loading ? (
          <LoadingState />
        ) : (
          <DocumentTable
            documents={documentsQuery.data?.items ?? []}
            warehouses={lookups.warehouses}
            onCancel={setCancelling}
            onPost={setPosting}
          />
        )}
      </Paper>
      <DocumentCreateDialog
        items={lookups.items}
        open={createOpen}
        organizationId={lookups.organizationId}
        units={lookups.units}
        warehouses={lookups.warehouses}
        onClose={() => setCreateOpen(false)}
      />
      <Dialog open={Boolean(posting)} onClose={() => setPosting(null)}>
        <DialogTitle>Провести документ?</DialogTitle>
        <DialogContent>
          <Typography>
            Після проведення документ змінить складські залишки. Редагування буде недоступне.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPosting(null)}>Скасувати</Button>
          <Button
            disabled={postMutation.isPending}
            variant="contained"
            onClick={() => {
              if (posting) {
                postMutation.mutate(posting.id);
                setPosting(null);
              }
            }}
          >
            Провести
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog open={Boolean(cancelling)} onClose={() => setCancelling(null)}>
        <DialogTitle>Скасувати проведений документ</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            <Typography>Система створить зворотні рухи і збереже початковий документ.</Typography>
            <TextField
              fullWidth
              label="Причина скасування"
              value={cancelReason}
              onChange={(event) => setCancelReason(event.target.value)}
            />
            {cancelMutation.error ? (
              <FriendlyError error={cancelMutation.error as ApiError} />
            ) : null}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCancelling(null)}>Закрити</Button>
          <Button
            color="error"
            disabled={!cancelReason.trim() || cancelMutation.isPending}
            variant="contained"
            onClick={() =>
              cancelling &&
              cancelMutation.mutate({ documentId: cancelling.id, reason: cancelReason })
            }
          >
            Скасувати документ
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
