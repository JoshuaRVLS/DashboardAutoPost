"use client";

import AccountContext from "@/context/AccountContext";
import { useState } from "react";

const AccountProvider = ({ children }) => {
  const [account, setAccount] = useState({});
  const data = {
    account,
    setAccount,
  };
  return (
    <AccountContext.Provider value={data}>{children}</AccountContext.Provider>
  );
};

export default AccountProvider;
