// =====================================================
// static/js/push_notifications.js
// base.html mein include karo
// =====================================================

const TRIKAL_PUSH = {

  // ─── Service Worker ready hone ka wait ───
  async init() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
      console.log('[Push] Browser support nahi hai');
      return;
    }

    const reg = await navigator.serviceWorker.ready;
    const existing = await reg.pushManager.getSubscription();

    if (existing) {
      // Already subscribed hai
      console.log('[Push] Already subscribed');
      this.updateUI(true);
    } else {
      this.updateUI(false);
    }
  },

  // ─── Permission maango aur subscribe karo ───
  async subscribe() {
    try {
      // Server se VAPID public key lo
      const keyRes  = await fetch('/api/push/vapid-key/');
      const keyData = await keyRes.json();

      const reg = await navigator.serviceWorker.ready;

      const subscription = await reg.pushManager.subscribe({
        userVisibleOnly:      true,
        applicationServerKey: this.urlBase64ToUint8Array(keyData.publicKey),
      });

      // Server pe save karo
      const saveRes = await fetch('/api/push/subscribe/', {
        method:  'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken':  this.getCsrf(),
        },
        body: JSON.stringify(subscription),
      });

      if (saveRes.ok) {
        console.log('[Push] Subscribed!');
        this.updateUI(true);
        this.showToast('🔔 सूचनाएं चालू हो गईं!');
      }
    } catch (err) {
      console.error('[Push] Subscribe error:', err);
      if (err.name === 'NotAllowedError') {
        this.showToast('⚠️ Notification permission denied। Browser settings से allow करें।');
      }
    }
  },

  // ─── Unsubscribe ───
  async unsubscribe() {
    const reg          = await navigator.serviceWorker.ready;
    const subscription = await reg.pushManager.getSubscription();

    if (subscription) {
      await fetch('/api/push/unsubscribe/', {
        method:  'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken':  this.getCsrf(),
        },
        body: JSON.stringify({ endpoint: subscription.endpoint }),
      });

      await subscription.unsubscribe();
      this.updateUI(false);
      this.showToast('🔕 सूचनाएं बंद कर दी गईं।');
    }
  },

  // ─── UI update karo ───
  updateUI(isSubscribed) {
    const btn = document.getElementById('push-toggle-btn');
    if (!btn) return;

    if (isSubscribed) {
      btn.textContent = '🔔 सूचनाएं बंद करें';
      btn.style.background = '#334155';
      btn.onclick = () => TRIKAL_PUSH.unsubscribe();
    } else {
      btn.textContent = '🔔 दैनिक सूचनाएं पाएं';
      btn.style.background = 'linear-gradient(45deg, #b71c1c, #e53935)';
      btn.onclick = () => TRIKAL_PUSH.subscribe();
    }
  },

  // ─── Toast message ───
  showToast(msg) {
    const toast = document.createElement('div');
    toast.style.cssText = `
      position: fixed; bottom: 80px; left: 50%; transform: translateX(-50%);
      background: #1e293b; color: #e2e8f0; padding: 12px 20px;
      border-radius: 20px; font-size: 14px; z-index: 9999;
      border: 1px solid #ffca28; box-shadow: 0 4px 15px rgba(0,0,0,0.4);
      animation: fadeIn 0.3s ease;
    `;
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
  },

  // ─── Helpers ───
  getCsrf() {
    return document.cookie.split(';')
      .find(c => c.trim().startsWith('csrftoken='))
      ?.split('=')[1] || '';
  },

  urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64  = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const raw     = window.atob(base64);
    return new Uint8Array([...raw].map(c => c.charCodeAt(0)));
  },
};

// Page load par init karo (sirf logged-in users ke liye)
document.addEventListener('DOMContentLoaded', () => {
  if (document.body.dataset.loggedIn === 'true') {
    TRIKAL_PUSH.init();
  }
});
