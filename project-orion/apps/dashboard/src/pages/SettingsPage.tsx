import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  User,
  Shield,
  Bell,
  CheckCircle,
  AlertCircle,
  Key,
  Lock,
  Globe,
  Clock,
  ShieldCheck,
  Save,
  Check,
  Eye,
  EyeOff,
  RefreshCw,
} from 'lucide-react';
import { userApi, authApi } from '../api/endpoints';
import type {
  UserProfileResponse,
  NotificationPreferences,
  UpdateProfileRequest,
} from '../api/types';
import { PageHeader } from '../components/common/PageHeader';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { Tabs, TabItem } from '../components/common/Tabs';
import { CardSkeleton } from '../components/common/Skeleton';
import { useToast } from '../components/common/Toast';

const TIMEZONES = [
  { value: 'UTC', label: 'UTC (Coordinated Universal Time)' },
  { value: 'America/New_York', label: 'America/New_York (EST/EDT, UTC-5/-4)' },
  { value: 'America/Chicago', label: 'America/Chicago (CST/CDT, UTC-6/-5)' },
  { value: 'America/Denver', label: 'America/Denver (MST/MDT, UTC-7/-6)' },
  { value: 'America/Los_Angeles', label: 'America/Los_Angeles (PST/PDT, UTC-8/-7)' },
  { value: 'Europe/London', label: 'Europe/London (GMT/BST, UTC+0/+1)' },
  { value: 'Europe/Frankfurt', label: 'Europe/Frankfurt (CET/CEST, UTC+1/+2)' },
  { value: 'Asia/Dubai', label: 'Asia/Dubai (GST, UTC+4)' },
  { value: 'Asia/Singapore', label: 'Asia/Singapore (SGT, UTC+8)' },
  { value: 'Asia/Tokyo', label: 'Asia/Tokyo (JST, UTC+9)' },
  { value: 'Australia/Sydney', label: 'Australia/Sydney (AEST/AEDT, UTC+10/+11)' },
];

export const SettingsPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const { showToast } = useToast();

  const activeTab = searchParams.get('tab') || 'profile';

  const setActiveTab = (tab: string) => {
    setSearchParams({ tab });
  };

  const [profile, setProfile] = useState<UserProfileResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Profile Form State
  const [fullName, setFullName] = useState('');
  const [timezone, setTimezone] = useState('UTC');
  const [isSavingProfile, setIsSavingProfile] = useState(false);

  // Security Form State
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [passwordSuccessMsg, setPasswordSuccessMsg] = useState<string | null>(null);
  const [passwordErrorMsg, setPasswordErrorMsg] = useState<string | null>(null);

  // Notifications State
  const [preferences, setPreferences] = useState<NotificationPreferences>({
    trade_events: true,
    risk_alerts: true,
    strategy_events: true,
    security_alerts: true,
  });
  const [isSavingPreferences, setIsSavingPreferences] = useState(false);

  const fetchProfile = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await userApi.getProfile();
      setProfile(data);
      setFullName(data.full_name || '');
      setTimezone(data.timezone || 'UTC');
      if (data.notification_preferences) {
        setPreferences(data.notification_preferences);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to load user profile');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  // Handle Profile Update
  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingProfile(true);
    try {
      const req: UpdateProfileRequest = {
        full_name: fullName.trim() || null,
        timezone: timezone.trim(),
      };
      const updated = await userApi.updateProfile(req);
      setProfile(updated);
      showToast('Your personal profile settings have been saved.', 'success');
    } catch (err: any) {
      showToast(err?.message || 'Could not update profile', 'error');
    } finally {
      setIsSavingProfile(false);
    }
  };

  // Password Policy Checks
  const hasMinLength = newPassword.length >= 8;
  const hasUppercase = /[A-Z]/.test(newPassword);
  const hasLowercase = /[a-z]/.test(newPassword);
  const hasDigit = /[0-9]/.test(newPassword);
  const hasSpecial = /[^A-Za-z0-9]/.test(newPassword);
  const isPasswordValid =
    hasMinLength && hasUppercase && hasLowercase && hasDigit && hasSpecial;
  const passwordsMatch = newPassword === confirmPassword && newPassword.length > 0;

  // Handle Password Change
  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordSuccessMsg(null);
    setPasswordErrorMsg(null);

    if (!isPasswordValid) {
      setPasswordErrorMsg('Please satisfy all password security requirements.');
      return;
    }

    if (!passwordsMatch) {
      setPasswordErrorMsg('New password and confirmation do not match.');
      return;
    }

    setIsChangingPassword(true);
    try {
      const res = await authApi.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });

      setPasswordSuccessMsg(
        res.message || 'Password successfully updated. All prior sessions have been revoked.'
      );
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      showToast('Security credentials updated and other sessions revoked.', 'success');

      // Refresh profile to update password_changed_at
      await fetchProfile();
    } catch (err: any) {
      setPasswordErrorMsg(err?.message || 'Failed to update password');
      showToast(err?.message || 'Verify current password and policy requirements', 'error');
    } finally {
      setIsChangingPassword(false);
    }
  };

  // Handle Notification Preferences Update
  const handleTogglePreference = (key: keyof NotificationPreferences) => {
    setPreferences((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const handleSavePreferences = async () => {
    setIsSavingPreferences(true);
    try {
      const updated = await userApi.updatePreferences(preferences);
      setPreferences(updated);
      showToast('Notification preferences have been persistently stored.', 'success');
    } catch (err: any) {
      showToast(err?.message || 'Could not update notification preferences', 'error');
    } finally {
      setIsSavingPreferences(false);
    }
  };

  const tabs: TabItem[] = [
    {
      id: 'profile',
      label: 'Profile & Account',
      icon: <User className="w-3.5 h-3.5" />,
    },
    {
      id: 'security',
      label: 'Security & Access',
      icon: <Shield className="w-3.5 h-3.5" />,
    },
    {
      id: 'notifications',
      label: 'Notification Preferences',
      icon: <Bell className="w-3.5 h-3.5" />,
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="User Settings"
        subtitle="Manage personal profile, institutional security credentials, and alert preferences."
        breadcrumbs={[{ label: 'Dashboard', path: '/dashboard' }, { label: 'Settings' }]}
        actions={
          <Button
            variant="outline"
            size="sm"
            onClick={fetchProfile}
            isLoading={isLoading}
            leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Refresh
          </Button>
        }
      />

      <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

      {isLoading && !profile ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <CardSkeleton />
          <CardSkeleton />
        </div>
      ) : error ? (
        <Card>
          <div className="p-8 text-center">
            <AlertCircle className="w-8 h-8 text-rose-400 mx-auto mb-3" />
            <h3 className="text-sm font-semibold text-slate-200 mb-1">Failed to Load Profile</h3>
            <p className="text-xs text-rose-300 mb-4">{error}</p>
            <Button variant="secondary" size="sm" onClick={fetchProfile}>
              Try Again
            </Button>
          </div>
        </Card>
      ) : (
        <>
          {/* ─── TAB 1: PROFILE & ACCOUNT ────────────────────────────────────────── */}
          {activeTab === 'profile' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Account Overview Sidebar Card */}
              <div className="lg:col-span-1 space-y-6">
                <Card title="Account Identity">
                  <div className="flex flex-col items-center text-center p-4">
                    <div className="w-20 h-20 rounded-full bg-gradient-to-tr from-sky-500/20 to-indigo-500/20 border-2 border-sky-500/40 flex items-center justify-center text-2xl font-bold font-mono text-sky-300 shadow-lg shadow-sky-950/40 mb-3">
                      {profile?.username.substring(0, 2).toUpperCase()}
                    </div>
                    <h2 className="text-base font-bold text-slate-100">{profile?.username}</h2>
                    <p className="text-xs text-slate-400 font-mono mt-0.5">{profile?.email}</p>

                    <div className="flex items-center gap-2 mt-3">
                      <Badge variant="success" dot>
                        ACTIVE
                      </Badge>
                      {profile?.email_verified ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-mono text-emerald-400 bg-emerald-950/40 border border-emerald-800/40 px-2 py-0.5 rounded-full">
                          <CheckCircle className="w-3 h-3" /> Verified
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] font-mono text-amber-400 bg-amber-950/40 border border-amber-800/40 px-2 py-0.5 rounded-full">
                          Unverified
                        </span>
                      )}
                      {profile?.is_superuser && (
                        <Badge variant="warning">SUPERUSER</Badge>
                      )}
                    </div>
                  </div>

                  <div className="mt-4 pt-4 border-t border-[#1E293B] space-y-2.5 text-xs font-mono">
                    <div className="flex justify-between items-center text-slate-400">
                      <span>User ID:</span>
                      <span className="text-slate-200 truncate max-w-[150px] font-bold">
                        {profile?.id}
                      </span>
                    </div>
                    <div className="flex justify-between items-center text-slate-400">
                      <span>Status:</span>
                      <span className="text-emerald-400 uppercase">{profile?.status}</span>
                    </div>
                    <div className="flex justify-between items-center text-slate-400">
                      <span>Member Since:</span>
                      <span className="text-slate-200">
                        {profile?.created_at
                          ? new Date(profile.created_at).toLocaleDateString()
                          : 'N/A'}
                      </span>
                    </div>
                  </div>
                </Card>
              </div>

              {/* Profile Details Form */}
              <div className="lg:col-span-2">
                <Card
                  title="Profile Information"
                  subtitle="Update personal details and local timezone for timestamps."
                >
                  <form onSubmit={handleSaveProfile} className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-mono font-medium text-slate-300 mb-1.5">
                          Username
                        </label>
                        <input
                          type="text"
                          value={profile?.username || ''}
                          disabled
                          className="w-full bg-[#0B101D] border border-[#1E293B] rounded-lg px-3 py-2 text-xs font-mono text-slate-400 cursor-not-allowed"
                        />
                        <span className="text-[10px] text-slate-500 mt-1 block">
                          Username cannot be changed.
                        </span>
                      </div>

                      <div>
                        <label className="block text-xs font-mono font-medium text-slate-300 mb-1.5">
                          Email Address
                        </label>
                        <input
                          type="email"
                          value={profile?.email || ''}
                          disabled
                          className="w-full bg-[#0B101D] border border-[#1E293B] rounded-lg px-3 py-2 text-xs font-mono text-slate-400 cursor-not-allowed"
                        />
                        <span className="text-[10px] text-slate-500 mt-1 block">
                          Email identity managed by organization.
                        </span>
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-mono font-medium text-slate-300 mb-1.5">
                        Full Name
                      </label>
                      <input
                        type="text"
                        value={fullName}
                        onChange={(e) => setFullName(e.target.value)}
                        placeholder="e.g. John Doe"
                        className="w-full bg-[#0B101D] border border-[#1E293B] rounded-lg px-3 py-2 text-xs font-sans text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-sky-500/60 focus:ring-1 focus:ring-sky-500/40"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-mono font-medium text-slate-300 mb-1.5">
                        Trading Timezone
                      </label>
                      <div className="relative">
                        <select
                          value={timezone}
                          onChange={(e) => setTimezone(e.target.value)}
                          className="w-full bg-[#0B101D] border border-[#1E293B] rounded-lg px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-sky-500/60 focus:ring-1 focus:ring-sky-500/40 cursor-pointer appearance-none"
                        >
                          {TIMEZONES.map((tz) => (
                            <option key={tz.value} value={tz.value} className="bg-[#0B101D]">
                              {tz.label}
                            </option>
                          ))}
                        </select>
                        <Globe className="w-4 h-4 text-slate-500 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                      </div>
                      <span className="text-[10px] text-slate-500 mt-1 block">
                        Used for session times, trade journal timestamps, and reports.
                      </span>
                    </div>

                    <div className="pt-4 border-t border-[#1E293B] flex justify-end">
                      <Button
                        type="submit"
                        variant="primary"
                        isLoading={isSavingProfile}
                        leftIcon={<Save className="w-3.5 h-3.5" />}
                      >
                        Save Changes
                      </Button>
                    </div>
                  </form>
                </Card>
              </div>
            </div>
          )}

          {/* ─── TAB 2: SECURITY & ACCESS ────────────────────────────────────────── */}
          {activeTab === 'security' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Change Password Card */}
              <div className="lg:col-span-2">
                <Card
                  title="Change Password"
                  subtitle="Update your institutional authentication credentials."
                >
                  {passwordSuccessMsg && (
                    <div className="p-3.5 mb-4 rounded-lg bg-emerald-950/40 border border-emerald-800/50 flex items-start gap-3">
                      <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                      <div className="text-xs text-emerald-200">
                        <p className="font-semibold">{passwordSuccessMsg}</p>
                        <p className="text-[11px] text-emerald-400 mt-0.5">
                          Other active browser sessions have been invalidated.
                        </p>
                      </div>
                    </div>
                  )}

                  {passwordErrorMsg && (
                    <div className="p-3.5 mb-4 rounded-lg bg-rose-950/40 border border-rose-800/50 flex items-start gap-3">
                      <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                      <p className="text-xs text-rose-200">{passwordErrorMsg}</p>
                    </div>
                  )}

                  <form onSubmit={handleChangePassword} className="space-y-4">
                    {/* Current Password */}
                    <div>
                      <label className="block text-xs font-mono font-medium text-slate-300 mb-1.5">
                        Current Password
                      </label>
                      <div className="relative">
                        <input
                          type={showCurrentPassword ? 'text' : 'password'}
                          value={currentPassword}
                          onChange={(e) => setCurrentPassword(e.target.value)}
                          required
                          placeholder="Enter current password"
                          className="w-full bg-[#0B101D] border border-[#1E293B] rounded-lg pl-3 pr-10 py-2 text-xs font-mono text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-sky-500/60 focus:ring-1 focus:ring-sky-500/40"
                        />
                        <button
                          type="button"
                          onClick={() => setShowCurrentPassword((prev) => !prev)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 cursor-pointer"
                        >
                          {showCurrentPassword ? (
                            <EyeOff className="w-4 h-4" />
                          ) : (
                            <Eye className="w-4 h-4" />
                          )}
                        </button>
                      </div>
                    </div>

                    {/* New Password */}
                    <div>
                      <label className="block text-xs font-mono font-medium text-slate-300 mb-1.5">
                        New Password
                      </label>
                      <div className="relative">
                        <input
                          type={showNewPassword ? 'text' : 'password'}
                          value={newPassword}
                          onChange={(e) => setNewPassword(e.target.value)}
                          required
                          placeholder="Enter new password"
                          className="w-full bg-[#0B101D] border border-[#1E293B] rounded-lg pl-3 pr-10 py-2 text-xs font-mono text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-sky-500/60 focus:ring-1 focus:ring-sky-500/40"
                        />
                        <button
                          type="button"
                          onClick={() => setShowNewPassword((prev) => !prev)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 cursor-pointer"
                        >
                          {showNewPassword ? (
                            <EyeOff className="w-4 h-4" />
                          ) : (
                            <Eye className="w-4 h-4" />
                          )}
                        </button>
                      </div>

                      {/* Password Requirements Checklist */}
                      <div className="mt-2.5 p-3 rounded-lg bg-[#0B101D] border border-[#1E293B] space-y-1.5">
                        <span className="text-[10px] font-mono text-slate-400 font-semibold block uppercase">
                          Password Security Policy:
                        </span>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-1 text-[11px] font-mono">
                          <div
                            className={`flex items-center gap-1.5 ${
                              hasMinLength ? 'text-emerald-400' : 'text-slate-500'
                            }`}
                          >
                            <Check className="w-3 h-3" /> Minimum 8 characters
                          </div>
                          <div
                            className={`flex items-center gap-1.5 ${
                              hasUppercase ? 'text-emerald-400' : 'text-slate-500'
                            }`}
                          >
                            <Check className="w-3 h-3" /> Uppercase letter (A-Z)
                          </div>
                          <div
                            className={`flex items-center gap-1.5 ${
                              hasLowercase ? 'text-emerald-400' : 'text-slate-500'
                            }`}
                          >
                            <Check className="w-3 h-3" /> Lowercase letter (a-z)
                          </div>
                          <div
                            className={`flex items-center gap-1.5 ${
                              hasDigit ? 'text-emerald-400' : 'text-slate-500'
                            }`}
                          >
                            <Check className="w-3 h-3" /> Number digit (0-9)
                          </div>
                          <div
                            className={`flex items-center gap-1.5 ${
                              hasSpecial ? 'text-emerald-400' : 'text-slate-500'
                            }`}
                          >
                            <Check className="w-3 h-3" /> Special character (!@#$%...)
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Confirm Password */}
                    <div>
                      <label className="block text-xs font-mono font-medium text-slate-300 mb-1.5">
                        Confirm New Password
                      </label>
                      <input
                        type="password"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        required
                        placeholder="Re-enter new password"
                        className={`w-full bg-[#0B101D] border rounded-lg px-3 py-2 text-xs font-mono text-slate-100 placeholder:text-slate-600 focus:outline-none focus:ring-1 ${
                          confirmPassword && !passwordsMatch
                            ? 'border-rose-500/70 focus:border-rose-500 focus:ring-rose-500/40'
                            : 'border-[#1E293B] focus:border-sky-500/60 focus:ring-sky-500/40'
                        }`}
                      />
                      {confirmPassword && !passwordsMatch && (
                        <span className="text-[10px] text-rose-400 mt-1 block">
                          Passwords do not match
                        </span>
                      )}
                    </div>

                    <div className="pt-4 border-t border-[#1E293B] flex justify-end">
                      <Button
                        type="submit"
                        variant="primary"
                        isLoading={isChangingPassword}
                        disabled={
                          !currentPassword ||
                          !isPasswordValid ||
                          !passwordsMatch ||
                          isChangingPassword
                        }
                        leftIcon={<Key className="w-3.5 h-3.5" />}
                      >
                        Update Password & Revoke Sessions
                      </Button>
                    </div>
                  </form>
                </Card>
              </div>

              {/* Security Status Card */}
              <div className="lg:col-span-1 space-y-6">
                <Card title="Session Governance">
                  <div className="space-y-4">
                    <div className="p-3 bg-[#0B101D] border border-[#1E293B] rounded-lg">
                      <div className="flex items-center gap-2 mb-1.5 text-xs font-semibold text-slate-200">
                        <Lock className="w-3.5 h-3.5 text-sky-400" />
                        <span>Fail-Closed Revocation</span>
                      </div>
                      <p className="text-[11px] text-slate-400 leading-relaxed">
                        Whenever your password is changed, Project ORION immediately revokes all prior
                        JWT bearer tokens and requires re-authentication on other devices.
                      </p>
                    </div>

                    <div className="p-3 bg-[#0B101D] border border-[#1E293B] rounded-lg text-xs font-mono space-y-2">
                      <div className="flex justify-between items-center text-slate-400">
                        <span>Last Password Change:</span>
                      </div>
                      <div className="text-slate-200 font-bold flex items-center gap-1.5">
                        <Clock className="w-3 h-3 text-sky-400" />
                        <span>
                          {profile?.password_changed_at
                            ? new Date(profile.password_changed_at).toLocaleString()
                            : 'Never'}
                        </span>
                      </div>
                    </div>

                    <div className="p-3 bg-[#0B101D] border border-[#1E293B] rounded-lg">
                      <div className="flex items-center gap-2 mb-1.5 text-xs font-semibold text-slate-200">
                        <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                        <span>Audit Logging</span>
                      </div>
                      <p className="text-[11px] text-slate-400 leading-relaxed">
                        All profile modifications, password resets, and session events are written
                        to the immutable audit log with cryptographic actors.
                      </p>
                    </div>
                  </div>
                </Card>
              </div>
            </div>
          )}

          {/* ─── TAB 3: NOTIFICATION PREFERENCES ─────────────────────────────────── */}
          {activeTab === 'notifications' && (
            <div className="max-w-3xl">
              <Card
                title="In-App Notification Preferences"
                subtitle="Choose which platform events dispatch notifications to the terminal bell."
              >
                <div className="space-y-4 divide-y divide-[#1E293B]">
                  {/* Trade Events */}
                  <div className="pt-3 first:pt-0 flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-slate-200">
                          Trade Execution Events
                        </span>
                        <span className="text-[10px] font-mono text-sky-400 bg-sky-950/40 border border-sky-800/40 px-1.5 py-0.2 rounded">
                          ORDER_FILLED
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-1">
                        Receive instant in-app alerts when paper orders are executed, filled, or
                        cancelled by the execution adapter.
                      </p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer shrink-0 mt-1">
                      <input
                        type="checkbox"
                        checked={preferences.trade_events}
                        onChange={() => handleTogglePreference('trade_events')}
                        className="sr-only peer"
                      />
                      <div className="w-9 h-5 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-sky-500"></div>
                    </label>
                  </div>

                  {/* Risk Alerts */}
                  <div className="pt-3 flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-slate-200">
                          Risk Control Alerts
                        </span>
                        <span className="text-[10px] font-mono text-amber-400 bg-amber-950/40 border border-amber-800/40 px-1.5 py-0.2 rounded">
                          RISK_BREACH
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-1">
                        Notifications for margin utilization warnings, maximum drawdown
                        thresholds, and risk governor triggers.
                      </p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer shrink-0 mt-1">
                      <input
                        type="checkbox"
                        checked={preferences.risk_alerts}
                        onChange={() => handleTogglePreference('risk_alerts')}
                        className="sr-only peer"
                      />
                      <div className="w-9 h-5 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-sky-500"></div>
                    </label>
                  </div>

                  {/* Strategy Events */}
                  <div className="pt-3 flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-slate-200">
                          Strategy & Optimization Signals
                        </span>
                        <span className="text-[10px] font-mono text-indigo-400 bg-indigo-950/40 border border-indigo-800/40 px-1.5 py-0.2 rounded">
                          STRATEGY_SIGNAL
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-1">
                        Alerts when quantitative models transition state, complete walk-forward
                        evaluations, or trigger signal regimes.
                      </p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer shrink-0 mt-1">
                      <input
                        type="checkbox"
                        checked={preferences.strategy_events}
                        onChange={() => handleTogglePreference('strategy_events')}
                        className="sr-only peer"
                      />
                      <div className="w-9 h-5 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-sky-500"></div>
                    </label>
                  </div>

                  {/* Security Alerts */}
                  <div className="pt-3 flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-slate-200">
                          Security & Authentication Notices
                        </span>
                        <span className="text-[10px] font-mono text-rose-400 bg-rose-950/40 border border-rose-800/40 px-1.5 py-0.2 rounded">
                          SECURITY_ALERT
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-1">
                        High-priority alerts regarding password updates, token expirations, and
                        organization invitation status changes.
                      </p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer shrink-0 mt-1">
                      <input
                        type="checkbox"
                        checked={preferences.security_alerts}
                        onChange={() => handleTogglePreference('security_alerts')}
                        className="sr-only peer"
                      />
                      <div className="w-9 h-5 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-sky-500"></div>
                    </label>
                  </div>
                </div>

                <div className="mt-6 pt-4 border-t border-[#1E293B] flex justify-end">
                  <Button
                    type="button"
                    variant="primary"
                    onClick={handleSavePreferences}
                    isLoading={isSavingPreferences}
                    leftIcon={<Save className="w-3.5 h-3.5" />}
                  >
                    Save Preferences
                  </Button>
                </div>
              </Card>
            </div>
          )}
        </>
      )}
    </div>
  );
};
export default SettingsPage;
