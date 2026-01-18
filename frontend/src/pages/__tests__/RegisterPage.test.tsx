import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
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
    const { container } = renderWithRouter(<RegisterPage />);
    expect(container.textContent).toContain('Create Account');
  });

  it('should have email input field', () => {
    renderWithRouter(<RegisterPage />);
    const emailInput = screen.getByPlaceholderText('you@example.com');
    expect(emailInput).toBeDefined();
  });

  it('should have password input field', () => {
    renderWithRouter(<RegisterPage />);
    const passwordInputs = screen.queryAllByPlaceholderText('••••••••');
    expect(passwordInputs.length > 0).toBe(true);
  });

  it('should have confirm password input field', () => {
    renderWithRouter(<RegisterPage />);
    const passwordInputs = screen.queryAllByPlaceholderText('••••••••');
    expect(passwordInputs.length >= 2).toBe(true);
  });

  it('should have submit button', () => {
    renderWithRouter(<RegisterPage />);
    const buttons = screen.getAllByRole('button');
    expect(buttons.length > 0).toBe(true);
  });

  it('should display page title', () => {
    renderWithRouter(<RegisterPage />);
    const title = screen.getByRole('heading', { level: 2 });
    expect(title.textContent).toContain('Create Account');
  });

  it('should display subtitle text', () => {
    const { container } = renderWithRouter(<RegisterPage />);
    expect(container.textContent).toContain('AI Trading Agent Platform');
  });

  it('should have email label', () => {
    renderWithRouter(<RegisterPage />);
    const emailLabel = screen.getByText('Email');
    expect(emailLabel).toBeDefined();
  });

  it('should have password label', () => {
    renderWithRouter(<RegisterPage />);
    const passwordLabels = screen.queryAllByText('Password');
    expect(passwordLabels.length > 0).toBe(true);
  });

  it('should have confirm password label', () => {
    renderWithRouter(<RegisterPage />);
    const confirmLabel = screen.getByText('Confirm Password');
    expect(confirmLabel).toBeDefined();
  });
});
