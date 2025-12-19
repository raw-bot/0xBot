export default function HomePage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-500 to-purple-600">
      <div className="text-center text-white space-y-8 p-8">
        <h1 className="text-6xl font-bold">AI Trading Agent</h1>
        <p className="text-2xl">Deploy autonomous AI traders with Claude, GPT-4, and more</p>
        <div className="space-x-4 pt-8">
          <a 
            href="/login" 
            className="inline-block px-8 py-3 bg-white text-blue-600 font-semibold rounded-lg hover:bg-gray-100 transition"
          >
            Sign In
          </a>
          <a 
            href="/register" 
            className="inline-block px-8 py-3 bg-transparent border-2 border-white text-white font-semibold rounded-lg hover:bg-white hover:text-blue-600 transition"
          >
            Get Started
          </a>
        </div>
      </div>
    </div>
  );
}