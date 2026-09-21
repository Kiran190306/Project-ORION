import React, { useEffect, useState, useMemo } from 'react';
import {
  Server,
  ShieldCheck,
  Activity,
  CheckCircle2,
  XCircle,
  Play,
  Square,
  RefreshCw,
  Plus,
  Send,
  Lock,
  Layers,
  FileCheck,
} from 'lucide-react';
import { brokerSandboxApi } from '../api/endpoints';
import type {
  BrokerProviderInfo,
  BrokerSandboxAccount,
  BrokerSandboxAccountCreateRequest,
  BrokerSandboxConnectResponse,
  BrokerSandboxOrderRequest,
  BrokerSandboxOrderResponse,
  BrokerSandboxPosition,
  BrokerSandboxReconciliationResponse,
} from '../api/types';
import { useAuth } from '../auth/AuthContext';
import { useOrganization } from '../auth/OrganizationContext';
import { Permission, hasPermission } from '../auth/permissions';
import { useToast } from '../components/common/Toast';

export const BrokerSandboxPage: React.FC = () => {
  const { user } = useAuth();
  const { currentRole } = useOrganization();
  const toast = useToast();

  const canConnect = hasPermission(currentRole, Permission.BROKER_SANDBOX_CONNECT, user?.is_superuser);
  const canExecute = hasPermission(currentRole, Permission.BROKER_SANDBOX_EXECUTE, user?.is_superuser);
  const canReconcile = hasPermission(currentRole, Permission.BROKER_SANDBOX_RECONCILE, user?.is_superuser);

  const [activeTab, setActiveTab] = useState<'connections' | 'terminal' | 'positions' | 'reconciliation'>('connections');
  const [providers, setProviders] = useState<BrokerProviderInfo[]>([]);
  const [accounts, setAccounts] = useState<BrokerSandboxAccount[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(null);
  const [positions, setPositions] = useState<BrokerSandboxPosition[]>([]);
  const [reconciliations, setReconciliations] = useState<BrokerSandboxReconciliationResponse[]>([]);
  const [activeReconciliation, setActiveReconciliation] = useState<BrokerSandboxReconciliationResponse | null>(null);

  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<boolean>(false);

  // New Connection Form
  const [showNewModal, setShowNewModal] = useState<boolean>(false);
  const [newAccName, setNewAccName] = useState<string>('');
  const [newAccProvider, setNewAccProvider] = useState<string>('MOCK');
  const [newAccExtId, setNewAccExtId] = useState<string>('demo-acc-01');
  const [newAccApiKey, setNewAccApiKey] = useState<string>('');

  // Order Ticket Form
  const [orderSymbol, setOrderSymbol] = useState<string>('EUR/USD');
  const [orderSide, setOrderSide] = useState<'BUY' | 'SELL'>('BUY');
  const [orderType, setOrderType] = useState<'MARKET' | 'LIMIT' | 'STOP'>('MARKET');
  const [orderQuantity, setOrderQuantity] = useState<number>(10000);
  const [orderPrice, setOrderPrice] = useState<number>(1.0850);
  const [orderStopLoss, setOrderStopLoss] = useState<number | undefined>(undefined);
  const [orderTakeProfit, setOrderTakeProfit] = useState<number | undefined>(undefined);
  const [lastOrderResult, setLastOrderResult] = useState<BrokerSandboxOrderResponse | null>(null);

  // Load initial data
  const fetchData = async () => {
    try {
      setLoading(true);
      const [provList, accList] = await Promise.all([
        brokerSandboxApi.listProviders(),
        brokerSandboxApi.listAccounts(),
      ]);
      setProviders(provList);
      setAccounts(accList);
      if (accList.length > 0 && !selectedAccountId) {
        setSelectedAccountId(accList[0].id);
      }
    } catch (err: any) {
      toast.show(err.message || 'Failed to load broker sandbox connections', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Fetch account specific data on selection
  useEffect(() => {
    if (!selectedAccountId) return;
    const fetchAccountDetails = async () => {
      try {
        const [posList, reconList] = await Promise.all([
          brokerSandboxApi.listPositions(selectedAccountId),
          brokerSandboxApi.listReconciliations(selectedAccountId),
        ]);
        setPositions(posList);
        setReconciliations(reconList);
        if (reconList.length > 0) {
          setActiveReconciliation(reconList[0]);
        }
      } catch (err: any) {
        // Silently catch or warn if disconnected
      }
    };
    fetchAccountDetails();
  }, [selectedAccountId]);

  const selectedAccount = useMemo(
    () => accounts.find((a) => a.id === selectedAccountId) || accounts[0] || null,
    [accounts, selectedAccountId]
  );

  // Handlers
  const handleConnect = async (accountId: string) => {
    if (!canConnect) {
      toast.show('Insufficient permission (BROKER_SANDBOX_CONNECT required)', 'error');
      return;
    }
    try {
      setActionLoading(true);
      const res: BrokerSandboxConnectResponse = await brokerSandboxApi.connectAccount(accountId);
      toast.show(`Connected to ${selectedAccount?.name} (${res.latency_ms.toFixed(1)}ms)`, 'success');
      await fetchData();
    } catch (err: any) {
      toast.show(err.message || 'Connection failed', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleDisconnect = async (accountId: string) => {
    if (!canConnect) {
      toast.show('Insufficient permission (BROKER_SANDBOX_CONNECT required)', 'error');
      return;
    }
    try {
      setActionLoading(true);
      await brokerSandboxApi.disconnectAccount(accountId);
      toast.show('Broker session disconnected', 'info');
      await fetchData();
    } catch (err: any) {
      toast.show(err.message || 'Disconnect failed', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCreateAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canConnect) {
      toast.show('Insufficient permission to configure broker sandboxes', 'error');
      return;
    }
    try {
      setActionLoading(true);
      const payload: BrokerSandboxAccountCreateRequest = {
        name: newAccName || `${newAccProvider} Sandbox`,
        provider: newAccProvider,
        environment: 'SANDBOX',
        account_id_external: newAccExtId,
        credentials: newAccApiKey ? { api_key: newAccApiKey } : undefined,
      };
      const created = await brokerSandboxApi.createAccount(payload);
      toast.show(`Sandbox connection '${created.name}' created with AES-GCM encryption`, 'success');
      setShowNewModal(false);
      setNewAccName('');
      setNewAccApiKey('');
      await fetchData();
      setSelectedAccountId(created.id);
    } catch (err: any) {
      toast.show(err.message || 'Account creation failed', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleSubmitOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAccount) {
      toast.show('Please select a sandbox account first', 'warning');
      return;
    }
    if (!canExecute) {
      toast.show('Permission denied (BROKER_SANDBOX_EXECUTE required)', 'error');
      return;
    }
    try {
      setActionLoading(true);
      const req: BrokerSandboxOrderRequest = {
        symbol: orderSymbol,
        side: orderSide,
        order_type: orderType,
        quantity: orderQuantity,
        price: orderType === 'MARKET' ? undefined : orderPrice,
        stop_loss: orderStopLoss,
        take_profit: orderTakeProfit,
      };
      const res = await brokerSandboxApi.submitOrder(selectedAccount.id, req);
      setLastOrderResult(res);
      toast.show(`Order ${res.order_id.slice(0, 8)} executed: ${res.status} (${res.filled_quantity} @ ${res.average_fill_price || 'MKT'})`, 'success');
      // Refresh positions
      const updatedPositions = await brokerSandboxApi.listPositions(selectedAccount.id);
      setPositions(updatedPositions);
    } catch (err: any) {
      toast.show(err.message || 'Order rejected by RiskEngine or Broker', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleReconcile = async () => {
    if (!selectedAccount) return;
    if (!canReconcile) {
      toast.show('Permission denied (BROKER_SANDBOX_RECONCILE required)', 'error');
      return;
    }
    try {
      setActionLoading(true);
      const res = await brokerSandboxApi.reconcileAccount(selectedAccount.id);
      setActiveReconciliation(res);
      const updatedHistory = await brokerSandboxApi.listReconciliations(selectedAccount.id);
      setReconciliations(updatedHistory);
      if (res.has_discrepancies) {
        toast.show(`Reconciliation completed with DISCREPANCIES (${res.discrepancies.length} mismatches)`, 'warning');
      } else {
        toast.show('State Reconciliation PASSED: 100% ledger-broker match', 'success');
      }
    } catch (err: any) {
      toast.show(err.message || 'Reconciliation failed', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Institutional Top Safety Banner */}
      <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-4 shadow-lg backdrop-blur-sm">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-emerald-500/20 p-2 text-emerald-400">
              <ShieldCheck className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold text-slate-100">Institutional Broker Sandbox Gateway</h1>
                <span className="rounded-full bg-emerald-500/20 px-2.5 py-0.5 text-xs font-semibold text-emerald-400 border border-emerald-500/30">
                  $0.00 Capital at Risk
                </span>
                <span className="rounded-full bg-blue-500/20 px-2 py-0.5 text-xs font-medium text-blue-400 border border-blue-500/30">
                  SANDBOX ONLY
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Deterministic Seeded Simulation & OANDA fxPractice v20 Demo Gateway. Live endpoints strictly blocked.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {canConnect && (
              <button
                onClick={() => setShowNewModal(true)}
                className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-500 transition-colors shadow-sm"
              >
                <Plus className="h-3.5 w-3.5" />
                Add Connection
              </button>
            )}
            <button
              onClick={fetchData}
              disabled={loading}
              className="inline-flex items-center gap-1.5 rounded-lg bg-slate-800 border border-slate-700 px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-700 transition-colors"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>
      </div>

      {/* Account Selector Pill Bar */}
      <div className="flex items-center justify-between gap-4 overflow-x-auto pb-1">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Active Gateway:</span>
          {accounts.map((acc) => (
            <button
              key={acc.id}
              onClick={() => setSelectedAccountId(acc.id)}
              className={`flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-medium border transition-all ${
                selectedAccountId === acc.id
                  ? 'border-indigo-500/50 bg-indigo-950/40 text-indigo-300'
                  : 'border-slate-800 bg-slate-900/60 text-slate-400 hover:border-slate-700 hover:text-slate-300'
              }`}
            >
              <span
                className={`h-2 w-2 rounded-full ${
                  acc.status === 'CONNECTED' ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'
                }`}
              />
              <span>{acc.name}</span>
              <span className="text-[10px] text-slate-500 uppercase">({acc.provider})</span>
            </button>
          ))}
          {accounts.length === 0 && !loading && (
            <span className="text-xs text-slate-500">No sandbox accounts configured. Create one above.</span>
          )}
        </div>

        {selectedAccount && (
          <div className="flex items-center gap-2 shrink-0">
            {selectedAccount.status === 'CONNECTED' ? (
              <button
                onClick={() => handleDisconnect(selectedAccount.id)}
                disabled={actionLoading || !canConnect}
                className="inline-flex items-center gap-1 rounded-md bg-amber-500/20 border border-amber-500/30 px-2.5 py-1 text-xs font-medium text-amber-300 hover:bg-amber-500/30 transition-colors"
              >
                <Square className="h-3 w-3" />
                Disconnect
              </button>
            ) : (
              <button
                onClick={() => handleConnect(selectedAccount.id)}
                disabled={actionLoading || !canConnect}
                className="inline-flex items-center gap-1 rounded-md bg-emerald-500/20 border border-emerald-500/30 px-2.5 py-1 text-xs font-medium text-emerald-300 hover:bg-emerald-500/30 transition-colors"
              >
                <Play className="h-3 w-3" />
                Connect Session
              </button>
            )}
            <button
              onClick={handleReconcile}
              disabled={actionLoading || !canReconcile || selectedAccount.status !== 'CONNECTED'}
              className="inline-flex items-center gap-1 rounded-md bg-slate-800 border border-slate-700 px-2.5 py-1 text-xs font-medium text-slate-200 hover:bg-slate-700 transition-colors disabled:opacity-50"
            >
              <FileCheck className="h-3 w-3 text-cyan-400" />
              Reconcile
            </button>
          </div>
        )}
      </div>

      {/* Main Tabs Navigation */}
      <div className="flex border-b border-slate-800">
        <button
          onClick={() => setActiveTab('connections')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors ${
            activeTab === 'connections'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-300'
          }`}
        >
          <Server className="h-4 w-4" />
          Connection Center
        </button>
        <button
          onClick={() => setActiveTab('terminal')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors ${
            activeTab === 'terminal'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-300'
          }`}
        >
          <Send className="h-4 w-4" />
          Sandbox Trading Terminal
        </button>
        <button
          onClick={() => setActiveTab('positions')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors ${
            activeTab === 'positions'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-300'
          }`}
        >
          <Layers className="h-4 w-4" />
          Positions & Balances
        </button>
        <button
          onClick={() => setActiveTab('reconciliation')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors ${
            activeTab === 'reconciliation'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-300'
          }`}
        >
          <FileCheck className="h-4 w-4" />
          Reconciliation Audit Center
        </button>
      </div>

      {/* TAB 1: CONNECTION CENTER */}
      {activeTab === 'connections' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {providers.map((p) => (
              <div
                key={p.provider}
                className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 shadow-sm space-y-4"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-100">{p.name}</h3>
                    <p className="text-xs text-slate-400 mt-1">{p.description}</p>
                  </div>
                  <span className="rounded bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 text-[10px] font-medium text-emerald-400">
                    {p.status}
                  </span>
                </div>
                <div className="space-y-1.5 text-xs text-slate-400">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Environment:</span>
                    <span className="font-mono text-slate-300">{p.environment}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Supported Orders:</span>
                    <span className="font-mono text-slate-300">{p.supported_order_types.join(', ')}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Instruments:</span>
                    <span className="font-mono text-slate-300">{p.supported_symbols.slice(0, 4).join(', ')}...</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">AES-GCM Auth:</span>
                    <span className="font-mono text-slate-300">{p.requires_credentials ? 'Required' : 'In-Memory Keyless'}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Accounts Table */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden">
            <div className="p-4 border-b border-slate-800 flex justify-between items-center">
              <h2 className="text-sm font-semibold text-slate-200">Registered Sandbox Connections</h2>
              <span className="text-xs text-slate-500">{accounts.length} Total Accounts</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-800/40 text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="py-2.5 px-4 font-medium">Name</th>
                    <th className="py-2.5 px-4 font-medium">Provider</th>
                    <th className="py-2.5 px-4 font-medium">External ID</th>
                    <th className="py-2.5 px-4 font-medium">Status</th>
                    <th className="py-2.5 px-4 font-medium">Masked Credentials</th>
                    <th className="py-2.5 px-4 font-medium text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-300">
                  {accounts.map((acc) => (
                    <tr key={acc.id} className="hover:bg-slate-800/20 transition-colors">
                      <td className="py-3 px-4 font-medium text-slate-200">{acc.name}</td>
                      <td className="py-3 px-4 font-mono text-slate-400">{acc.provider}</td>
                      <td className="py-3 px-4 font-mono text-slate-400">{acc.account_id_external}</td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-medium border ${
                            acc.status === 'CONNECTED'
                              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                              : 'bg-slate-500/10 text-slate-400 border-slate-500/30'
                          }`}
                        >
                          <span
                            className={`h-1.5 w-1.5 rounded-full ${
                              acc.status === 'CONNECTED' ? 'bg-emerald-400' : 'bg-slate-500'
                            }`}
                          />
                          {acc.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-500">
                        {Object.entries(acc.credentials_masked || {}).map(([k, v]) => (
                          <span key={k} className="inline-block bg-slate-800 rounded px-1.5 py-0.5 text-[11px] mr-1">
                            {k}: {v}
                          </span>
                        ))}
                        {Object.keys(acc.credentials_masked || {}).length === 0 && 'None'}
                      </td>
                      <td className="py-3 px-4 text-right">
                        {acc.status === 'CONNECTED' ? (
                          <button
                            onClick={() => handleDisconnect(acc.id)}
                            disabled={actionLoading || !canConnect}
                            className="text-amber-400 hover:text-amber-300 text-xs font-medium"
                          >
                            Disconnect
                          </button>
                        ) : (
                          <button
                            onClick={() => handleConnect(acc.id)}
                            disabled={actionLoading || !canConnect}
                            className="text-emerald-400 hover:text-emerald-300 text-xs font-medium"
                          >
                            Connect
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                  {accounts.length === 0 && (
                    <tr>
                      <td colSpan={6} className="py-6 text-center text-slate-500">
                        No sandbox accounts created. Click "Add Connection" to start.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: SANDBOX TRADING TERMINAL */}
      {activeTab === 'terminal' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Order Ticket */}
          <div className="lg:col-span-1 rounded-xl border border-slate-800 bg-slate-900/40 p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
                <Send className="h-4 w-4 text-indigo-400" />
                Sandbox Order Ticket
              </h3>
              <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/40 border border-emerald-500/30 px-2 py-0.5 rounded">
                Zero Risk Gate
              </span>
            </div>

            <form onSubmit={handleSubmitOrder} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-400 mb-1 font-medium">Instrument / Symbol</label>
                <select
                  value={orderSymbol}
                  onChange={(e) => setOrderSymbol(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-slate-200 focus:border-indigo-500 focus:outline-hidden"
                >
                  <option value="EUR/USD">EUR/USD</option>
                  <option value="GBP/USD">GBP/USD</option>
                  <option value="USD/JPY">USD/JPY</option>
                  <option value="AUD/USD">AUD/USD</option>
                  <option value="USD/CHF">USD/CHF</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setOrderSide('BUY')}
                  className={`py-2 rounded-lg font-bold transition-colors ${
                    orderSide === 'BUY'
                      ? 'bg-emerald-600 text-white'
                      : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                  }`}
                >
                  BUY / LONG
                </button>
                <button
                  type="button"
                  onClick={() => setOrderSide('SELL')}
                  className={`py-2 rounded-lg font-bold transition-colors ${
                    orderSide === 'SELL'
                      ? 'bg-rose-600 text-white'
                      : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                  }`}
                >
                  SELL / SHORT
                </button>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-slate-400 mb-1 font-medium">Order Type</label>
                  <select
                    value={orderType}
                    onChange={(e) => setOrderType(e.target.value as any)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-slate-200 focus:border-indigo-500 focus:outline-hidden"
                  >
                    <option value="MARKET">MARKET</option>
                    <option value="LIMIT">LIMIT</option>
                    <option value="STOP">STOP</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-400 mb-1 font-medium">Quantity (Units)</label>
                  <input
                    type="number"
                    min="100"
                    step="100"
                    value={orderQuantity}
                    onChange={(e) => setOrderQuantity(Number(e.target.value))}
                    className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-slate-200 focus:border-indigo-500 focus:outline-hidden"
                  />
                </div>
              </div>

              {orderType !== 'MARKET' && (
                <div>
                  <label className="block text-slate-400 mb-1 font-medium">Price</label>
                  <input
                    type="number"
                    step="0.00001"
                    value={orderPrice}
                    onChange={(e) => setOrderPrice(Number(e.target.value))}
                    className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-slate-200 focus:border-indigo-500 focus:outline-hidden"
                  />
                </div>
              )}

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-slate-400 mb-1 font-medium">Stop Loss (Optional)</label>
                  <input
                    type="number"
                    step="0.00001"
                    placeholder="e.g. 1.08000"
                    value={orderStopLoss || ''}
                    onChange={(e) => setOrderStopLoss(e.target.value ? Number(e.target.value) : undefined)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-slate-200 focus:border-indigo-500 focus:outline-hidden"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 mb-1 font-medium">Take Profit (Optional)</label>
                  <input
                    type="number"
                    step="0.00001"
                    placeholder="e.g. 1.09500"
                    value={orderTakeProfit || ''}
                    onChange={(e) => setOrderTakeProfit(e.target.value ? Number(e.target.value) : undefined)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-slate-200 focus:border-indigo-500 focus:outline-hidden"
                  />
                </div>
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={actionLoading || !canExecute || !selectedAccount || selectedAccount.status !== 'CONNECTED'}
                  className="w-full py-2.5 rounded-lg bg-indigo-600 font-semibold text-white hover:bg-indigo-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-md"
                >
                  {actionLoading ? 'Processing Pipeline...' : `Execute Sandbox ${orderSide}`}
                </button>
              </div>

              <div className="p-3 bg-slate-800/40 rounded-lg border border-slate-800 text-[11px] text-slate-400 space-y-1">
                <div className="flex items-center gap-1.5 text-slate-300 font-semibold">
                  <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                  Mandatory Execution Chain:
                </div>
                <p>Request &rarr; Entitlement Check &rarr; RiskEngine &rarr; OrderValidator &rarr; Adapter &rarr; Sandbox</p>
              </div>
            </form>
          </div>

          {/* Execution Pipeline Inspector & Last Response */}
          <div className="lg:col-span-2 space-y-4">
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 shadow-sm space-y-4">
              <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                <Activity className="h-4 w-4 text-cyan-400" />
                Execution Receipt & Audit Trail
              </h3>
              {lastOrderResult ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                    <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-800">
                      <span className="text-slate-500 block">Status</span>
                      <span className="font-bold text-emerald-400">{lastOrderResult.status}</span>
                    </div>
                    <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-800">
                      <span className="text-slate-500 block">Filled Units</span>
                      <span className="font-mono font-bold text-slate-200">{lastOrderResult.filled_quantity}</span>
                    </div>
                    <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-800">
                      <span className="text-slate-500 block">Avg Fill Price</span>
                      <span className="font-mono font-bold text-slate-200">{lastOrderResult.average_fill_price || 'N/A'}</span>
                    </div>
                    <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-800">
                      <span className="text-slate-500 block">Execution Latency</span>
                      <span className="font-mono font-bold text-cyan-400">{lastOrderResult.latency_ms.toFixed(1)}ms</span>
                    </div>
                  </div>
                  <div className="bg-slate-950/70 p-3 rounded-lg border border-slate-800 text-xs font-mono text-slate-300 space-y-1">
                    <div><span className="text-slate-500">Internal Order ID:</span> {lastOrderResult.order_id}</div>
                    <div><span className="text-slate-500">Broker Reference:</span> {lastOrderResult.broker_order_id}</div>
                    <div><span className="text-slate-500">Instrument:</span> {lastOrderResult.symbol} ({lastOrderResult.side} {lastOrderResult.order_type})</div>
                    <div><span className="text-slate-500">Timestamp:</span> {new Date(lastOrderResult.timestamp).toISOString()}</div>
                  </div>
                </div>
              ) : (
                <div className="py-12 text-center text-slate-500 text-xs">
                  No orders executed yet in this session. Submit an order using the ticket on the left.
                </div>
              )}
            </div>

            {/* Quick Open Positions on Terminal */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 shadow-sm space-y-3">
              <h3 className="text-sm font-semibold text-slate-200">Current Gateway Positions ({positions.length})</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-800/40 text-slate-400 border-b border-slate-800">
                    <tr>
                      <th className="py-2 px-3 font-medium">Symbol</th>
                      <th className="py-2 px-3 font-medium">Side</th>
                      <th className="py-2 px-3 font-medium">Quantity</th>
                      <th className="py-2 px-3 font-medium">Entry Price</th>
                      <th className="py-2 px-3 font-medium">Unrealized PnL</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-300">
                    {positions.map((pos) => (
                      <tr key={pos.symbol}>
                        <td className="py-2.5 px-3 font-bold text-slate-200">{pos.symbol}</td>
                        <td className="py-2.5 px-3">
                          <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${pos.quantity >= 0 ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>
                            {pos.quantity >= 0 ? 'LONG' : 'SHORT'}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 font-mono">{Math.abs(pos.quantity)}</td>
                        <td className="py-2.5 px-3 font-mono">{pos.average_entry_price}</td>
                        <td className={`py-2.5 px-3 font-mono font-bold ${pos.unrealized_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                          ${pos.unrealized_pnl.toFixed(2)}
                        </td>
                      </tr>
                    ))}
                    {positions.length === 0 && (
                      <tr>
                        <td colSpan={5} className="py-4 text-center text-slate-500 text-xs">
                          Flat. No open positions reported by broker sandbox.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: POSITIONS & BALANCES */}
      {activeTab === 'positions' && (
        <div className="space-y-6">
          <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 shadow-sm space-y-4">
            <h3 className="text-sm font-semibold text-slate-200">Sandbox Broker Ledger & Positions</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-800/40 text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="py-2.5 px-4 font-medium">Symbol</th>
                    <th className="py-2.5 px-4 font-medium">Side</th>
                    <th className="py-2.5 px-4 font-medium">Net Units</th>
                    <th className="py-2.5 px-4 font-medium">Avg Entry Price</th>
                    <th className="py-2.5 px-4 font-medium">Current Price</th>
                    <th className="py-2.5 px-4 font-medium">Unrealized PnL</th>
                    <th className="py-2.5 px-4 font-medium">Margin Allocated</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-300">
                  {positions.map((pos) => (
                    <tr key={pos.symbol}>
                      <td className="py-3 px-4 font-bold text-slate-100">{pos.symbol}</td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${pos.quantity >= 0 ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>
                          {pos.quantity >= 0 ? 'LONG' : 'SHORT'}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono">{Math.abs(pos.quantity)}</td>
                      <td className="py-3 px-4 font-mono">{pos.average_entry_price}</td>
                      <td className="py-3 px-4 font-mono">{pos.current_price || pos.average_entry_price}</td>
                      <td className={`py-3 px-4 font-mono font-bold ${pos.unrealized_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        ${pos.unrealized_pnl.toFixed(2)}
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-400">${pos.margin_used.toFixed(2)}</td>
                    </tr>
                  ))}
                  {positions.length === 0 && (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-slate-500">
                        No active positions on this sandbox account.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: RECONCILIATION AUDIT CENTER */}
      {activeTab === 'reconciliation' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* History Column */}
          <div className="lg:col-span-1 rounded-xl border border-slate-800 bg-slate-900/40 p-5 shadow-sm space-y-4">
            <div className="flex justify-between items-center pb-2 border-b border-slate-800">
              <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
                <FileCheck className="h-4 w-4 text-cyan-400" />
                Audit Snapshots
              </h3>
              <button
                onClick={handleReconcile}
                disabled={actionLoading || !canReconcile || !selectedAccount || selectedAccount.status !== 'CONNECTED'}
                className="inline-flex items-center gap-1 rounded bg-cyan-600 px-2 py-1 text-[11px] font-medium text-white hover:bg-cyan-500 transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`h-3 w-3 ${actionLoading ? 'animate-spin' : ''}`} />
                Run Audit
              </button>
            </div>

            <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
              {reconciliations.map((rec) => (
                <div
                  key={rec.id}
                  onClick={() => setActiveReconciliation(rec)}
                  className={`p-3 rounded-lg border cursor-pointer transition-all ${
                    activeReconciliation?.id === rec.id
                      ? 'border-cyan-500/50 bg-cyan-950/30'
                      : 'border-slate-800 bg-slate-900/60 hover:border-slate-700'
                  }`}
                >
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-mono text-slate-300 font-semibold">{rec.id.slice(0, 10)}</span>
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                        rec.status === 'MATCHED'
                          ? 'bg-emerald-500/20 text-emerald-400'
                          : 'bg-amber-500/20 text-amber-400'
                      }`}
                    >
                      {rec.status}
                    </span>
                  </div>
                  <div className="flex justify-between items-center text-[11px] text-slate-400 mt-1.5">
                    <span>{new Date(rec.timestamp).toLocaleTimeString()}</span>
                    <span>{rec.discrepancies.length} Discrepancies</span>
                  </div>
                </div>
              ))}
              {reconciliations.length === 0 && (
                <p className="text-center py-8 text-slate-500 text-xs">
                  No reconciliation audits performed yet. Click "Run Audit" above.
                </p>
              )}
            </div>
          </div>

          {/* Snapshot Inspector */}
          <div className="lg:col-span-2 space-y-4">
            {activeReconciliation ? (
              <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 shadow-sm space-y-5">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-100">
                      Audit Snapshot: {activeReconciliation.id}
                    </h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Evaluated against Broker State at {new Date(activeReconciliation.timestamp).toLocaleString()}
                    </p>
                  </div>
                  <span
                    className={`px-2.5 py-1 rounded text-xs font-bold ${
                      activeReconciliation.status === 'MATCHED'
                        ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                        : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                    }`}
                  >
                    {activeReconciliation.status}
                  </span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div className="bg-slate-800/40 p-3 rounded-lg border border-slate-800">
                    <span className="text-slate-500 block">Resolution Policy</span>
                    <span className="font-semibold text-slate-200">{activeReconciliation.resolution_policy}</span>
                  </div>
                  <div className="bg-slate-800/40 p-3 rounded-lg border border-slate-800">
                    <span className="text-slate-500 block">State Preserved</span>
                    <span className="font-semibold text-emerald-400">
                      {activeReconciliation.internal_state_preserved ? '100% (No Mutate)' : 'Altered'}
                    </span>
                  </div>
                  <div className="bg-slate-800/40 p-3 rounded-lg border border-slate-800">
                    <span className="text-slate-500 block">Manual Review</span>
                    <span className="font-semibold text-slate-200">
                      {activeReconciliation.manual_review_required ? 'Required' : 'None Needed'}
                    </span>
                  </div>
                  <div className="bg-slate-800/40 p-3 rounded-lg border border-slate-800">
                    <span className="text-slate-500 block">Discrepancies</span>
                    <span className="font-semibold text-slate-200">
                      {activeReconciliation.discrepancies.length} Total
                    </span>
                  </div>
                </div>

                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                    Discrepancy Ledger Diff
                  </h4>
                  {activeReconciliation.discrepancies.length > 0 ? (
                    <div className="overflow-x-auto rounded-lg border border-slate-800">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-slate-800/60 text-slate-400 border-b border-slate-800">
                          <tr>
                            <th className="py-2 px-3 font-medium">Entity</th>
                            <th className="py-2 px-3 font-medium">ID</th>
                            <th className="py-2 px-3 font-medium">Field</th>
                            <th className="py-2 px-3 font-medium">Internal Ledger</th>
                            <th className="py-2 px-3 font-medium">Broker Sandbox</th>
                            <th className="py-2 px-3 font-medium">Severity</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800 text-slate-300">
                          {activeReconciliation.discrepancies.map((d, i) => (
                            <tr key={i}>
                              <td className="py-2.5 px-3 font-medium text-slate-200">{d.entity}</td>
                              <td className="py-2.5 px-3 font-mono text-slate-400">{d.id}</td>
                              <td className="py-2.5 px-3 font-mono text-slate-300">{d.field}</td>
                              <td className="py-2.5 px-3 font-mono text-amber-400">{String(d.internal_value)}</td>
                              <td className="py-2.5 px-3 font-mono text-cyan-400">{String(d.broker_value)}</td>
                              <td className="py-2.5 px-3">
                                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-400">
                                  {d.severity}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="p-6 bg-slate-900/60 border border-slate-800 rounded-lg text-center text-xs text-emerald-400">
                      <CheckCircle2 className="h-6 w-6 mx-auto mb-2 text-emerald-400" />
                      Zero state drift detected. Internal ledger matches external sandbox state with 100% precision.
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-12 text-center text-slate-500 text-xs">
                Select an audit snapshot from the list to view the discrepancy diff.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Add Connection Modal */}
      {showNewModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-xl border border-slate-800 bg-slate-900 p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <Lock className="h-4 w-4 text-indigo-400" />
                Register Broker Sandbox Connection
              </h3>
              <button onClick={() => setShowNewModal(false)} className="text-slate-400 hover:text-slate-200">
                <XCircle className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleCreateAccount} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-400 mb-1 font-medium">Provider</label>
                <select
                  value={newAccProvider}
                  onChange={(e) => setNewAccProvider(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-slate-200 focus:border-indigo-500 focus:outline-hidden"
                >
                  <option value="MOCK">Deterministic Mock Broker ($0 Risk)</option>
                  <option value="OANDA_PRACTICE">OANDA fxPractice v20 Demo</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-400 mb-1 font-medium">Connection Name</label>
                <input
                  type="text"
                  placeholder="e.g. Primary Alpha Sandbox"
                  value={newAccName}
                  onChange={(e) => setNewAccName(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-slate-200 focus:border-indigo-500 focus:outline-hidden"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1 font-medium">External Account ID</label>
                <input
                  type="text"
                  placeholder="e.g. 101-004-1234567"
                  value={newAccExtId}
                  onChange={(e) => setNewAccExtId(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-slate-200 focus:border-indigo-500 focus:outline-hidden"
                />
              </div>

              {newAccProvider === 'OANDA_PRACTICE' && (
                <div>
                  <label className="block text-slate-400 mb-1 font-medium">OANDA Practice API Token</label>
                  <input
                    type="password"
                    placeholder="Enter sandbox personal access token"
                    value={newAccApiKey}
                    onChange={(e) => setNewAccApiKey(e.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-slate-200 focus:border-indigo-500 focus:outline-hidden"
                  />
                  <p className="text-[10px] text-slate-500 mt-1">
                    Encrypted with AES-256-GCM. Raw token is never logged or exposed in API responses.
                  </p>
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowNewModal(false)}
                  className="rounded-lg bg-slate-800 border border-slate-700 px-3 py-1.5 font-medium text-slate-300 hover:bg-slate-700 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="rounded-lg bg-indigo-600 px-3 py-1.5 font-medium text-white hover:bg-indigo-500 transition-colors disabled:opacity-50"
                >
                  {actionLoading ? 'Encrypting & Saving...' : 'Save Connection'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default BrokerSandboxPage;
