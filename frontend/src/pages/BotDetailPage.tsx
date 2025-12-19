import { useParams } from 'react-router-dom';

export default function BotDetailPage() {
  const { botId } = useParams();

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <h2 className="text-3xl font-bold mb-6">Bot Details</h2>
        <p className="text-gray-600">Bot ID: {botId}</p>
        <p className="text-gray-600 mt-4">Bot details will be displayed here...</p>
      </div>
    </div>
  );
}