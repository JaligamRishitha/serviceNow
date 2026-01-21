import React from 'react';
import ServiceRequestForm from './ServiceRequestForm';

const PasswordResetForm = () => {
  const handleSubmit = (formData) => {
    console.log('Password reset request:', formData);
    alert('Password reset request submitted successfully! You will receive an email with further instructions.');
  };

  return (
    <ServiceRequestForm
      title="Need a password reset?"
      description="Click here to access the password portal. Click here for info on Password Manager. Please provide your details below and we'll help you reset your password."
      formType="password"
      onSubmit={handleSubmit}
    />
  );
};

export default PasswordResetForm;