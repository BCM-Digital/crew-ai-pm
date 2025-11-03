export default function Home() {
  return (
    <main className="min-h-screen p-8">
      <h1 className="text-3xl font-bold mb-4">PM Agent Dashboard</h1>
      <p className="text-gray-600 mb-8">Today&apos;s Overview - Coming Soon</p>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div className="border rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-2">Today&apos;s Plan</h2>
          <p className="text-gray-500">View daily plan and top 5 tasks</p>
        </div>

        <div className="border rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-2">Projects</h2>
          <p className="text-gray-500">MCU, QRIDA, Uniform Link, LTC, SureMesh</p>
        </div>

        <div className="border rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-2">Approvals</h2>
          <p className="text-gray-500">Pending approval requests</p>
        </div>

        <div className="border rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-2">Search</h2>
          <p className="text-gray-500">Search work graph</p>
        </div>

        <div className="border rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-2">Recent Activity</h2>
          <p className="text-gray-500">Latest tool invocations and flows</p>
        </div>

        <div className="border rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-2">Settings</h2>
          <p className="text-gray-500">Configuration and preferences</p>
        </div>
      </div>
    </main>
  );
}
