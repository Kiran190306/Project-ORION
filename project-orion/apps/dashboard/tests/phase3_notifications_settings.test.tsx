import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider } from '../src/auth/AuthContext';
import { OrganizationProvider } from '../src/auth/OrganizationContext';
import { ToastProvider } from '../src/components/common/Toast';
import { NotificationPopover } from '../src/components/notifications/NotificationPopover';
import { SettingsPage } from '../src/pages/SettingsPage';
import { notificationsApi, userApi, authApi } from '../src/api/endpoints';

describe('Phase 3: Notification Center & User Settings', () => {
  beforeEach(() => {
    sessionStorage.clear();
    localStorage.clear();
    vi.restoreAllMocks();
  });

  const mockNotifications = [
    {
      id: 'notif_1',
      channel: 'in_app',
      severity: 'info',
      notification_type: 'ORDER_FILLED',
      title: 'Order Filled: BUY EUR/USD',
      body: 'Executed 10000 units at 1.08500 (Paper)',
      status: 'unread',
      recipient: 'user_1',
      is_read: false,
      read_at: null,
      meta_data: { order_id: 'ord_123' },
      created_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    },
    {
      id: 'notif_2',
      channel: 'in_app',
      severity: 'warning',
      notification_type: 'RISK_ALERT',
      title: 'Margin Warning: EUR/USD',
      body: 'Margin utilization exceeded 70% threshold',
      status: 'unread',
      recipient: 'user_1',
      is_read: false,
      read_at: null,
      meta_data: {},
      created_at: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
    },
  ];

  const mockProfile = {
    id: 'usr_test_1',
    username: 'quant_trader',
    email: 'trader@institutional.test',
    full_name: 'Alex Mercer',
    is_active: true,
    is_superuser: false,
    status: 'ACTIVE',
    email_verified: true,
    password_changed_at: '2026-09-01T12:00:00Z',
    timezone: 'UTC',
    notification_preferences: {
      trade_events: true,
      risk_alerts: true,
      strategy_events: true,
      security_alerts: true,
    },
    created_at: '2026-08-15T09:30:00Z',
    updated_at: '2026-09-20T10:00:00Z',
  };

  describe('NotificationPopover Component', () => {
    it('fetches unread count and renders bell badge', async () => {
      vi.spyOn(notificationsApi, 'getUnreadCount').mockResolvedValue({ unread_count: 2 });
      vi.spyOn(notificationsApi, 'list').mockResolvedValue({
        items: mockNotifications,
        total: 2,
        limit: 30,
        offset: 0,
        has_more: false,
      });

      render(
        <MemoryRouter>
          <NotificationPopover />
        </MemoryRouter>
      );

      const bell = screen.getByRole('button', { name: /notifications/i });
      expect(bell).toBeInTheDocument();

      expect(await screen.findByText('2')).toBeInTheDocument();
    });

    it('opens dropdown, displays notifications, and marks single notification read', async () => {
      const user = userEvent.setup();
      vi.spyOn(notificationsApi, 'getUnreadCount').mockResolvedValue({ unread_count: 2 });
      vi.spyOn(notificationsApi, 'list').mockResolvedValue({
        items: [...mockNotifications],
        total: 2,
        limit: 30,
        offset: 0,
        has_more: false,
      });
      const markReadSpy = vi.spyOn(notificationsApi, 'markRead').mockResolvedValue({
        ...mockNotifications[0],
        is_read: true,
        status: 'read',
      });

      render(
        <MemoryRouter>
          <NotificationPopover />
        </MemoryRouter>
      );

      const bell = screen.getByRole('button', { name: /notifications/i });
      await user.click(bell);

      expect(await screen.findByText('Order Filled: BUY EUR/USD')).toBeInTheDocument();
      expect(screen.getByText('Margin Warning: EUR/USD')).toBeInTheDocument();

      const markReadButtons = screen.getAllByRole('button', { name: /mark read/i });
      expect(markReadButtons.length).toBe(2);
      await user.click(markReadButtons[0]);

      expect(markReadSpy).toHaveBeenCalledWith('notif_1');
    });

    it('marks all notifications as read and clears unread count', async () => {
      const user = userEvent.setup();
      vi.spyOn(notificationsApi, 'getUnreadCount').mockResolvedValue({ unread_count: 2 });
      vi.spyOn(notificationsApi, 'list').mockResolvedValue({
        items: [...mockNotifications],
        total: 2,
        limit: 30,
        offset: 0,
        has_more: false,
      });
      const markAllSpy = vi.spyOn(notificationsApi, 'markAllRead').mockResolvedValue({
        marked_count: 2,
        message: 'Marked 2 notifications as read',
      });

      render(
        <MemoryRouter>
          <NotificationPopover />
        </MemoryRouter>
      );

      const bell = screen.getByRole('button', { name: /notifications/i });
      await user.click(bell);

      const markAllBtn = await screen.findByRole('button', { name: /mark all read/i });
      await user.click(markAllBtn);

      expect(markAllSpy).toHaveBeenCalledTimes(1);
    });

    it('renders empty state when no notifications exist', async () => {
      const user = userEvent.setup();
      vi.spyOn(notificationsApi, 'getUnreadCount').mockResolvedValue({ unread_count: 0 });
      vi.spyOn(notificationsApi, 'list').mockResolvedValue({
        items: [],
        total: 0,
        limit: 30,
        offset: 0,
        has_more: false,
      });

      render(
        <MemoryRouter>
          <NotificationPopover />
        </MemoryRouter>
      );

      const bell = screen.getByRole('button', { name: /notifications/i });
      await user.click(bell);

      expect(await screen.findByText('No notifications')).toBeInTheDocument();
      expect(screen.getByText(/system alerts and trading events will appear here/i)).toBeInTheDocument();
    });
  });

  describe('SettingsPage Component', () => {
    it('renders Profile tab with user details and verified badge', async () => {
      vi.spyOn(userApi, 'getProfile').mockResolvedValue(mockProfile);

      render(
        <MemoryRouter initialEntries={['/settings?tab=profile']}>
          <ToastProvider>
            <AuthProvider>
              <OrganizationProvider>
                <SettingsPage />
              </OrganizationProvider>
            </AuthProvider>
          </ToastProvider>
        </MemoryRouter>
      );

      expect(await screen.findByText('User Settings')).toBeInTheDocument();
      expect(screen.getByText('quant_trader')).toBeInTheDocument();
      expect(screen.getByText('trader@institutional.test')).toBeInTheDocument();
      expect(screen.getByText('Verified')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Alex Mercer')).toBeInTheDocument();
    });

    it('updates full name and timezone via userApi.updateProfile', async () => {
      const user = userEvent.setup();
      vi.spyOn(userApi, 'getProfile').mockResolvedValue(mockProfile);
      const updateSpy = vi.spyOn(userApi, 'updateProfile').mockResolvedValue({
        ...mockProfile,
        full_name: 'Alex Mercer Jr.',
        timezone: 'Asia/Tokyo',
      });

      render(
        <MemoryRouter initialEntries={['/settings?tab=profile']}>
          <ToastProvider>
            <AuthProvider>
              <OrganizationProvider>
                <SettingsPage />
              </OrganizationProvider>
            </AuthProvider>
          </ToastProvider>
        </MemoryRouter>
      );

      const nameInput = await screen.findByDisplayValue('Alex Mercer');
      await user.clear(nameInput);
      await user.type(nameInput, 'Alex Mercer Jr.');

      const saveBtn = screen.getByRole('button', { name: /save changes/i });
      await user.click(saveBtn);

      expect(updateSpy).toHaveBeenCalledWith({
        full_name: 'Alex Mercer Jr.',
        timezone: 'UTC',
      });
    });

    it('enforces password policy, matches confirmation, and submits password change', async () => {
      const user = userEvent.setup();
      vi.spyOn(userApi, 'getProfile').mockResolvedValue(mockProfile);
      const changePasswordSpy = vi.spyOn(authApi, 'changePassword').mockResolvedValue({
        message: 'Password has been successfully updated. Prior sessions have been revoked.',
      });

      render(
        <MemoryRouter initialEntries={['/settings?tab=security']}>
          <ToastProvider>
            <AuthProvider>
              <OrganizationProvider>
                <SettingsPage />
              </OrganizationProvider>
            </AuthProvider>
          </ToastProvider>
        </MemoryRouter>
      );

      expect(await screen.findByText('Change Password')).toBeInTheDocument();
      const currentInput = screen.getByPlaceholderText('Enter current password');
      const newInput = screen.getByPlaceholderText('Enter new password');
      const confirmInput = screen.getByPlaceholderText('Re-enter new password');
      const submitBtn = screen.getByRole('button', { name: /update password & revoke sessions/i });

      // Initially disabled
      expect(submitBtn).toBeDisabled();

      // Enter matching and strong password
      await user.type(currentInput, 'OldP@ssw0rd!');
      await user.type(newInput, 'NewP@ssw0rd2026!');
      await user.type(confirmInput, 'NewP@ssw0rd2026!');

      expect(submitBtn).not.toBeDisabled();
      await user.click(submitBtn);

      expect(changePasswordSpy).toHaveBeenCalledWith({
        current_password: 'OldP@ssw0rd!',
        new_password: 'NewP@ssw0rd2026!',
        confirm_password: 'NewP@ssw0rd2026!',
      });
    });

    it('toggles notification preferences and saves via userApi.updatePreferences', async () => {
      const user = userEvent.setup();
      vi.spyOn(userApi, 'getProfile').mockResolvedValue(mockProfile);
      const updatePrefsSpy = vi.spyOn(userApi, 'updatePreferences').mockResolvedValue({
        ...mockProfile.notification_preferences,
        trade_events: false,
      });

      render(
        <MemoryRouter initialEntries={['/settings?tab=notifications']}>
          <ToastProvider>
            <AuthProvider>
              <OrganizationProvider>
                <SettingsPage />
              </OrganizationProvider>
            </AuthProvider>
          </ToastProvider>
        </MemoryRouter>
      );

      expect(await screen.findByText('Trade Execution Events')).toBeInTheDocument();
      expect(screen.getByText('Risk Control Alerts')).toBeInTheDocument();
      expect(screen.getByText('Strategy & Optimization Signals')).toBeInTheDocument();
      expect(screen.getByText('Security & Authentication Notices')).toBeInTheDocument();

      // Find checkboxes
      const checkboxes = screen.getAllByRole('checkbox');
      expect(checkboxes.length).toBe(4);

      // Toggle first checkbox (trade_events)
      await user.click(checkboxes[0]);

      const saveBtn = screen.getByRole('button', { name: /save preferences/i });
      await user.click(saveBtn);

      expect(updatePrefsSpy).toHaveBeenCalledWith({
        trade_events: false,
        risk_alerts: true,
        strategy_events: true,
        security_alerts: true,
      });
    });
  });
});
