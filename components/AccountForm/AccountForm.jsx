"use client";

import React, { useState } from "react";
import "./AccountForm.css";
import { motion } from "motion/react";
import toast, { ToastBar } from "react-hot-toast";
import axios from "axios";
import { useSession } from "next-auth/react";

const AccountForm = ({ openForm, setOpenForm }) => {
  const [token, setToken] = useState("");
  const { data: session, update } = useSession();

  const addAccount = async (e) => {
    let toastId = toast.loading("Verifying User...");
    try {
      const response = await axios.post(
        "http://localhost:8080/api/v1/users/accounts",
        {
          id: session?.user?.userId,
          token,
        }
      );
      toast.remove(toastId);
      await update();
      toast.success(response.data.msg);
    } catch (error) {
      toast.remove(toastId);
      toast.error(error.response.data.msg);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: openForm ? 100 : 0 }}
      className="fixed flex flex-col gap-2 left-[10.5rem] top-[12.5rem] bg-innerBackground p-2 rounded-md shadow-md border border-black"
    >
      <input
        onChange={(e) => setToken(e.target.value)}
        value={token}
        className="input h-1"
        type="password"
        placeholder="Token"
      />
      <button onClick={addAccount} className="btn h-fit">
        Add
      </button>
      <button onClick={() => setOpenForm(false)} className="btn-cancel">
        Cancel
      </button>
    </motion.div>
  );
};

export default AccountForm;
