"use client";

import AccountContext from "@/context/AccountContext";
import { motion } from "motion/react";
import { useSession } from "next-auth/react";
import React, { useContext, useEffect, useState } from "react";
import "./AccountSelect.css";

const AccountSelect = () => {
  const { data: session } = useSession();
  const { currentAccount, setCurrentAccount } = useContext(AccountContext);
  const [open, setOpen] = useState(false);

  const handleChange = (e) => {
    setOpen(false);
    localStorage.setItem("selectedAccount", e.target.innerText);
    setCurrentAccount(e.target.innerText);
  };

  return (
    session && (
      <div className="w-full">
        <motion.div onClick={() => setOpen(!open)} className="accounts">
          {currentAccount || "Select Account"}
        </motion.div>
        <motion.div
          className="account-menu"
          initial={{ opacity: 0, height: 0 }}
          animate={{
            opacity: open ? 100 : 0,
            height: open ? "fit-content" : 0,
          }}
          transition={{
            staggerChildren: 0.5,
            delayChildren: 1,
          }}
        >
          {Object.keys(session?.user?.accounts).map((accountName, key) => (
            <motion.span
              className={`${
                currentAccount === accountName && "text-btnBackground"
              }`}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              onClick={handleChange}
              key={key}
            >
              {accountName}
            </motion.span>
          ))}
          <button className="border border-btnBackground p-2 rounded-full my-2 transition-all duration-300 hover:bg-btnBackground text-white">
            Add
          </button>
          <p className="text-center  border border-black shadow-xl p-2 uppercase">
            {session?.user?.max_bots -
              Object.keys(session?.user?.accounts).length}{" "}
            bots left
          </p>
        </motion.div>
      </div>
    )
  );
};

export default AccountSelect;
