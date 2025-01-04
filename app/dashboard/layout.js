import Navbar from "@/components/Navbar/Navbar";
import AccountProvider from "@/providers/AccountProvider";

export const metadata = {
  title: "User Dashboard",
  description: "User dashboard",
};

export default function DashboardLayout({ children }) {
  return (
    <AccountProvider>
      <Navbar />
      {children}
    </AccountProvider>
  );
}
