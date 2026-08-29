import Layout from '../components/Layout';

// Day 1: one generic shell. Role-based rendering (admin vs member) and
// route protection based on `profiles.status` land Day 2-3.
export default function Dashboard() {
  return (
    <Layout>
      <h1>Dashboard</h1>
      <p>Files, chat, and admin tools will appear here as they're built out.</p>
    </Layout>
  );
}