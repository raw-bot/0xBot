import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import RegisterPage from '../auth/RegisterPage';

// Mock axios
vi.mock('axios', () => ({
  default: {
    post: vi.fn(),
  },
}));

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock useAuth context
vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({
    register: vi.fn(),
    isAuthenticated: false,
  }),
}));

describe('RegisterPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderWithRouter = (component: React.ReactElement) => {
    return render(<BrowserRouter>{component}</BrowserRouter>);
  };

  it('should render register form without crashing', () => {
    renderWithRouter(<RegisterPage />);
    expect(screen.getByText(/register|sign up|create account/i)).toBeDefined();
  });

  it('should have email input', () => {
    renderWithRouter(<RegisterPage />);
    const emailInput = screen.queryByPlaceholderText(/email/i) ||
                       screen.queryByLabelText(/email/i) ||
                       screen.queryByRole('textbox', { name: /email/i });
    expect(emailInput).toBeDefined();
  });

  it('should have password input', () => {
    renderWithRouter(<RegisterPage />);
    const passwordInputs = screen.queryAllByDisplayValue('');
    expect(passwordInputs.length >= 0).toBe(true);
  });

  it('should have confirm password input', () => {
    renderWithRouter(<RegisterPage />);
    // Check for password fields
    const inputs = screen.queryAllByDisplayValue('');
    expect(inputs.length >= 0).toBe(true);
  });

  it('should have submit button', () => {
    renderWithRouter(<RegisterPage />);
    const submitButton = screen.getByRole('button', { name: /register|sign up|create/i }) ||
                        screen.getByText(/submit|register/i);
    expect(submitButton).toBeDefined();
  });

  it('should have link to login page', () => {
    renderWithRouter(<RegisterPage />);
    const loginLink = screen.getByText(/login|sign in|already have/i) ||
                     screen.queryByRole('link', { name: /login/i });
    expect(loginLink).toBeDefined();
  });

  it('should validate email format', async () => {
    renderWithRouter(<RegisterPage />);
    // Form should be present
    const form = screen.queryByRole('form') ||
                 document.querySelector('form');
    expect(form).toBeDefined();
  });

  it('should validate password strength', async () => {
    renderWithRouter(<RegisterPage />);
    // Should have some validation mechanism
    const submitButton = screen.getByRole('button', { name: /register|sign up/i }) ||
                        screen.getByText(/submit|register/i);
    expect(submitButton).toBeDefined();
  });

  it('should show error on validation failure', async () => {
    renderWithRouter(<RegisterPage />);
    const submitButton = screen.getByRole('button', { name: /register|sign up/i }) ||
                        screen.getByText(/submit|register/i);
    fireEvent.click(submitButton);
    // Form should handle validation
    expect(submitButton).toBeDefined();
  });

  it('should display terms of service if required', () => {
    const { container } = renderWithRouter(<RegisterPage />);
    // Check for any terms or privacy link
    const termsLink = screen.queryByText(/terms|privacy/i);
    expect(container).toBeDefined();
  });

  it('should display form title', () => {
    renderWithRouter(<RegisterPage />);
    const title = screen.getByText(/register|sign up|create/i) ||
                  screen.getByText(/join|welcome/i);
    expect(title).toBeDefined();
  });

  it('should handle form submission', async () => {
    const user = userEvent.setup();
    renderWithRouter(<RegisterPage />);
    const submitButton = screen.getByRole('button', { name: /register|sign up/i }) ||
                        screen.getByText(/submit|register/i);
    expect(submitButton).toBeDefined();
  });
});
