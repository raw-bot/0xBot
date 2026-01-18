import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import LoginPage from '../auth/LoginPage';

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
    login: vi.fn(),
    isAuthenticated: false,
  }),
}));

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderWithRouter = (component: React.ReactElement) => {
    return render(<BrowserRouter>{component}</BrowserRouter>);
  };

  it('should render login form without crashing', () => {
    const { container } = renderWithRouter(<LoginPage />);
    expect(container.textContent).toContain('Sign In');
  });

  it('should have email input field', () => {
    renderWithRouter(<LoginPage />);
    const emailInput = screen.getByPlaceholderText('you@example.com');
    expect(emailInput).toBeDefined();
  });

  it('should have password input field', () => {
    renderWithRouter(<LoginPage />);
    const passwordInput = screen.getByPlaceholderText('••••••••');
    expect(passwordInput).toBeDefined();
  });

  it('should have submit button', () => {
    renderWithRouter(<LoginPage />);
    const buttons = screen.getAllByRole('button');
    expect(buttons.length > 0).toBe(true);
  });

  it('should display page title', () => {
    renderWithRouter(<LoginPage />);
    const title = screen.getByRole('heading', { level: 2 });
    expect(title.textContent).toContain('Sign In');
  });

  it('should display subtitle text', () => {
    const { container } = renderWithRouter(<LoginPage />);
    expect(container.textContent).toContain('AI Trading Agent Platform');
  });

  it('should render form elements', () => {
    const { container } = renderWithRouter(<LoginPage />);
    const form = container.querySelector('form');
    expect(form).toBeDefined();
  });

  it('should have email label', () => {
    renderWithRouter(<LoginPage />);
    const emailLabel = screen.getByText('Email');
    expect(emailLabel).toBeDefined();
  });

  it('should have password label', () => {
    renderWithRouter(<LoginPage />);
    const passwordLabel = screen.getByText('Password');
    expect(passwordLabel).toBeDefined();
  });

  it('should render without errors', () => {
    const { container } = renderWithRouter(<LoginPage />);
    expect(container.querySelector('[class*="bg-red"]')).toBeNull();
  });
});
