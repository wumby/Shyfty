import { Link, useLocation } from 'react-router-dom';

const EFFECTIVE_DATE = 'May 6, 2026';

function Terms() {
  return (
    <div className="prose-legal">
      <h1>Terms of Service</h1>
      <p className="lead">Effective {EFFECTIVE_DATE}</p>

      <h2>1. Acceptance</h2>
      <p>By creating an account or using Shyfty, you agree to these terms. If you don't agree, don't use the service.</p>

      <h2>2. What Shyfty Is</h2>
      <p>Shyfty is a sports analytics platform that surfaces statistical shifts in player and team performance. Data is sourced from public box scores and may contain errors or delays. We make no guarantees about accuracy, completeness, or timeliness.</p>

      <h2>3. Your Account</h2>
      <p>You must be 13 or older to create an account. You are responsible for keeping your credentials secure. Don't share your password or let others use your account.</p>

      <h2>4. Acceptable Use</h2>
      <p>You agree not to: post spam, harassment, or illegal content; scrape or automate requests to our API; attempt to access other users' accounts; reverse-engineer the service; or use the platform for commercial data resale without permission.</p>

      <h2>5. Your Content</h2>
      <p>Comments and reactions you post remain yours. By posting, you grant Shyfty a non-exclusive, royalty-free license to store and display that content as part of the service. We may remove content that violates these terms.</p>

      <h2>6. Termination</h2>
      <p>We may suspend or delete accounts that violate these terms, at our discretion. You can delete your account at any time from your account settings.</p>

      <h2>7. Disclaimers</h2>
      <p>The service is provided "as is" without warranty of any kind. We are not liable for decisions made based on data shown on Shyfty, including any financial decisions related to sports betting or fantasy sports.</p>

      <h2>8. Changes</h2>
      <p>We may update these terms. Continued use after changes are posted means you accept the new terms.</p>

      <h2>9. Contact</h2>
      <p>Questions? Email <a href="mailto:jackzieg@gmail.com">jackzieg@gmail.com</a>.</p>
    </div>
  );
}

function Privacy() {
  return (
    <div className="prose-legal">
      <h1>Privacy Policy</h1>
      <p className="lead">Effective {EFFECTIVE_DATE}</p>

      <h2>1. What We Collect</h2>
      <p><strong>Account data:</strong> email address and optional display name when you sign up.</p>
      <p><strong>Activity data:</strong> comments, reactions, and player/team follows you create.</p>
      <p><strong>Session data:</strong> a session cookie to keep you signed in, and a CSRF token cookie for security. No third-party tracking cookies.</p>

      <h2>2. How We Use It</h2>
      <p>We use your data solely to provide and improve Shyfty — personalizing your feed, showing your activity, and keeping your account secure. We do not sell, rent, or share your personal data with third parties for advertising.</p>

      <h2>3. Cookies</h2>
      <p>We set two cookies: a session cookie (<code>shyfty_session</code>) and a security cookie (<code>shyfty_csrf</code>). Both are necessary for the service to function. Neither is used for tracking.</p>

      <h2>4. Data Retention</h2>
      <p>Your data is retained as long as your account exists. When you delete your account, your personal data is removed from our systems within 30 days.</p>

      <h2>5. Security</h2>
      <p>Passwords are hashed using PBKDF2-SHA256. Session tokens are stored hashed server-side. All production traffic is encrypted via HTTPS.</p>

      <h2>6. Your Rights</h2>
      <p>You can update your display name, change your password, or delete your account from the account settings page. To request a copy of your data or full deletion, email <a href="mailto:jackzieg@gmail.com">jackzieg@gmail.com</a>.</p>

      <h2>7. Changes</h2>
      <p>We may update this policy. We'll update the effective date at the top when we do.</p>

      <h2>8. Contact</h2>
      <p>Privacy questions: <a href="mailto:jackzieg@gmail.com">jackzieg@gmail.com</a>.</p>
    </div>
  );
}

export function LegalPage() {
  const { pathname } = useLocation();
  const isPrivacy = pathname === '/privacy';

  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      <div className="mb-8 flex gap-4 border-b border-border pb-4">
        <Link
          to="/terms"
          className={`text-sm font-semibold transition ${!isPrivacy ? 'text-ink' : 'text-muted hover:text-ink'}`}
        >
          Terms of Service
        </Link>
        <Link
          to="/privacy"
          className={`text-sm font-semibold transition ${isPrivacy ? 'text-ink' : 'text-muted hover:text-ink'}`}
        >
          Privacy Policy
        </Link>
      </div>

      {isPrivacy ? <Privacy /> : <Terms />}

      <div className="mt-12 border-t border-border pt-6">
        <Link to="/" className="text-sm text-muted transition hover:text-ink">← Back to Shyfty</Link>
      </div>
    </div>
  );
}
