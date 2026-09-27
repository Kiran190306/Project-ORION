import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Bell,
  CheckCheck,
  Check,
  AlertCircle,
  AlertTriangle,
  Info,
  Clock,
  RefreshCw,
  Settings,
  X,
} from 'lucide-react';
import { notificationsApi } from '../../api/endpoints';
import type { NotificationItem } from '../../api/types';

export const NotificationPopover: React.FC = () => {
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState(false);
  const [isMarkingAll, setIsMarkingAll] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [unreadOnly, setUnreadOnly] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);

  // Poll unread count periodically
  const fetchUnreadCount = useCallback(async () => {
    try {
      const res = await notificationsApi.getUnreadCount();
      setUnreadCount(res.unread_count);
    } catch {
      // Fail silently for background badge poll
    }
  }, []);

  const fetchNotifications = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await notificationsApi.list({ limit: 30, unread_only: unreadOnly });
      setNotifications(res.items);
      const unread = res.items.filter((item) => !item.is_read).length;
      if (!unreadOnly) {
        setUnreadCount(unread);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to load notifications');
    } finally {
      setIsLoading(false);
    }
  }, [unreadOnly]);

  useEffect(() => {
    fetchUnreadCount();
    const interval = setInterval(fetchUnreadCount, 30000);
    return () => clearInterval(interval);
  }, [fetchUnreadCount]);

  useEffect(() => {
    if (isOpen) {
      fetchNotifications();
    }
  }, [isOpen, fetchNotifications]);

  // Click outside listener
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  const handleMarkRead = async (id: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    try {
      await notificationsApi.markRead(id);
      setNotifications((prev) =>
        prev.map((item) => (item.id === id ? { ...item, is_read: true, status: 'read' } : item))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (err: any) {
      console.error('Failed to mark notification as read:', err);
    }
  };

  const handleMarkAllRead = async () => {
    setIsMarkingAll(true);
    try {
      await notificationsApi.markAllRead();
      setNotifications((prev) =>
        prev.map((item) => ({ ...item, is_read: true, status: 'read' }))
      );
      setUnreadCount(0);
    } catch (err: any) {
      console.error('Failed to mark all as read:', err);
    } finally {
      setIsMarkingAll(false);
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />;
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />;
      default:
        return <Info className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />;
    }
  };

  const formatTimestamp = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      const now = new Date();
      const diffMs = now.getTime() - d.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      if (diffMins < 1) return 'Just now';
      if (diffMins < 60) return `${diffMins}m ago`;
      const diffHours = Math.floor(diffMins / 60);
      if (diffHours < 24) return `${diffHours}h ago`;
      return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="relative" ref={containerRef}>
      {/* Popover Bell Button */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="relative p-2 text-slate-400 hover:text-slate-200 hover:bg-[#141E33] rounded-lg transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-sky-500/50"
        title="Terminal Notifications"
        aria-label={`Notifications (${unreadCount} unread)`}
        aria-expanded={isOpen}
      >
        <Bell className="w-4 h-4" />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 min-w-[16px] h-4 px-1 bg-sky-500 text-white font-mono text-[9px] font-bold rounded-full flex items-center justify-center animate-pulse">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown Panel */}
      {isOpen && (
        <div
          role="dialog"
          aria-label="Notifications Popover"
          className="absolute right-0 mt-2 w-80 sm:w-96 bg-[#0E1626] border border-[#1E293B] rounded-xl shadow-2xl shadow-black/80 z-50 overflow-hidden font-sans flex flex-col max-h-[520px]"
        >
          {/* Header */}
          <div className="px-4 py-3 border-b border-[#1E293B] bg-[#141E33] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-100 text-sm">Notifications</span>
              {unreadCount > 0 && (
                <span className="bg-sky-500/20 text-sky-400 border border-sky-500/30 text-[10px] font-mono font-bold px-2 py-0.5 rounded-full">
                  {unreadCount} unread
                </span>
              )}
            </div>
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={handleMarkAllRead}
                disabled={isMarkingAll || unreadCount === 0}
                className="text-[11px] font-mono text-slate-400 hover:text-sky-400 disabled:opacity-40 disabled:hover:text-slate-400 flex items-center gap-1 px-2 py-1 rounded transition-colors cursor-pointer"
                title="Mark all notifications as read"
              >
                <CheckCheck className="w-3.5 h-3.5" />
                <span>Mark all read</span>
              </button>
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                className="text-slate-400 hover:text-slate-200 p-1 rounded transition-colors"
                aria-label="Close notifications popover"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Filter Bar */}
          <div className="px-4 py-2 bg-[#0A101D] border-b border-[#1E293B] flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setUnreadOnly(false)}
                className={`px-2 py-0.5 rounded font-mono text-[11px] transition-colors ${
                  !unreadOnly
                    ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40 font-semibold'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                All
              </button>
              <button
                type="button"
                onClick={() => setUnreadOnly(true)}
                className={`px-2 py-0.5 rounded font-mono text-[11px] transition-colors ${
                  unreadOnly
                    ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40 font-semibold'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Unread only
              </button>
            </div>
            <button
              type="button"
              onClick={fetchNotifications}
              disabled={isLoading}
              className="text-slate-400 hover:text-slate-200 p-1 rounded"
              title="Refresh notifications"
            >
              <RefreshCw className={`w-3 h-3 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
          </div>

          {/* List Content */}
          <div className="flex-1 overflow-y-auto divide-y divide-[#1E293B]">
            {isLoading && notifications.length === 0 ? (
              <div className="p-8 flex flex-col items-center justify-center text-slate-400">
                <RefreshCw className="w-5 h-5 animate-spin text-sky-400 mb-2" />
                <span className="text-xs font-mono">Loading notifications...</span>
              </div>
            ) : error ? (
              <div className="p-6 text-center">
                <AlertCircle className="w-6 h-6 text-rose-400 mx-auto mb-2" />
                <p className="text-xs text-rose-300 mb-3">{error}</p>
                <button
                  type="button"
                  onClick={fetchNotifications}
                  className="px-3 py-1 bg-[#141E33] hover:bg-[#1A2742] text-xs font-mono text-slate-200 rounded border border-[#1E293B]"
                >
                  Retry
                </button>
              </div>
            ) : notifications.length === 0 ? (
              <div className="p-8 text-center flex flex-col items-center justify-center">
                <div className="w-10 h-10 rounded-full bg-[#141E33] border border-[#1E293B] flex items-center justify-center text-slate-500 mb-2">
                  <Bell className="w-5 h-5" />
                </div>
                <p className="text-xs font-semibold text-slate-300">
                  {unreadOnly ? 'No unread notifications' : 'No notifications'}
                </p>
                <p className="text-[11px] text-slate-500 mt-1">
                  System alerts and trading events will appear here.
                </p>
              </div>
            ) : (
              notifications.map((item) => (
                <div
                  key={item.id}
                  onClick={() => !item.is_read && handleMarkRead(item.id)}
                  className={`p-3.5 hover:bg-[#141E33]/70 transition-colors flex items-start gap-3 cursor-pointer ${
                    !item.is_read ? 'bg-[#121D30]/40' : 'opacity-80'
                  }`}
                >
                  {getSeverityIcon(item.severity)}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2 mb-0.5">
                      <span
                        className={`text-xs font-semibold truncate ${
                          !item.is_read ? 'text-slate-100 font-bold' : 'text-slate-300'
                        }`}
                      >
                        {item.title}
                      </span>
                      <span className="text-[10px] font-mono text-slate-500 shrink-0 flex items-center gap-1">
                        <Clock className="w-2.5 h-2.5" />
                        {formatTimestamp(item.created_at)}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
                      {item.body}
                    </p>
                    <div className="flex items-center justify-between mt-2 pt-1 border-t border-[#1E293B]/40">
                      <span className="text-[9px] font-mono text-slate-500 uppercase">
                        {item.notification_type}
                      </span>
                      {!item.is_read ? (
                        <button
                          type="button"
                          onClick={(e) => handleMarkRead(item.id, e)}
                          className="text-[10px] font-mono text-sky-400 hover:text-sky-300 flex items-center gap-1 cursor-pointer"
                          title="Mark as read"
                        >
                          <Check className="w-3 h-3" />
                          <span>Mark read</span>
                        </button>
                      ) : (
                        <span className="text-[9px] font-mono text-slate-600 flex items-center gap-0.5">
                          <CheckCheck className="w-2.5 h-2.5" /> Read
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Footer */}
          <div className="p-2.5 bg-[#0E1626] border-t border-[#1E293B] flex items-center justify-between text-xs">
            <button
              type="button"
              onClick={() => {
                setIsOpen(false);
                navigate('/settings?tab=notifications');
              }}
              className="text-[11px] font-mono text-slate-400 hover:text-sky-400 flex items-center gap-1.5 px-2 py-1 rounded transition-colors cursor-pointer"
            >
              <Settings className="w-3.5 h-3.5" />
              <span>Notification Settings</span>
            </button>
            <span className="text-[10px] font-mono text-slate-500">Project ORION Real-Time</span>
          </div>
        </div>
      )}
    </div>
  );
};
export default NotificationPopover;
