import Navbar from "@/components/Navbar/Navbar";

export const metadata = {
  title: "User Dashboard",
  description: "User dashboard",
};

export default function DashboardLayout({ children }) {
  return (
    <>
      <Navbar />
      {children}
    </>
  );
}
