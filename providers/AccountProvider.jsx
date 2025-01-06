"use client";

import AccountContext from "@/context/AccountContext";
import { useSession } from "next-auth/react";
import { useState, useEffect } from "react";

const AccountProvider = ({ children }) => {
  const { data: session } = useSession();
  const [currentAccount, setCurrentAccount] = useState("");
  const data = {
    currentAccount,
    setCurrentAccount,
  };

  useEffect(() => {
    const accountName = localStorage.getItem("selectedAccount");
    if (!accountName) return;
    if (session?.user.accounts) {
      if (Object.keys(session?.user.accounts).length === 0) {
        localStorage.removeItem("selectedAccount");
        setCurrentAccount(null);
        return;
      }
      Object.keys(session?.user.accounts).forEach((account, key) => {
        if (account === accountName) {
          setCurrentAccount(account);
          return;
        }
      });
    }
  }, [session, currentAccount]);

  return (
    <AccountContext.Provider value={data}>{children}</AccountContext.Provider>
  );
};

export default AccountProvider;
