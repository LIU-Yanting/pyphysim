#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for the modules in the comp package.

Each module has several doctests that we run in addition to the unittests
defined here.
"""

__revision__ = "$Revision$"

# xxxxxxxxxx Add the parent folder to the python path. xxxxxxxxxxxxxxxxxxxx
import sys
import os
parent_dir = os.path.split(os.path.abspath(os.path.dirname(__file__)))[0]
sys.path.append(parent_dir)
# xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
import unittest
import doctest

import numpy as np

from comm import channels, modulators
from comp import comp
from util.misc import least_right_singular_vectors, randn_c
from util.conversion import dB2Linear, linear2dB
from subspace.projections import calcProjectionMatrix


# UPDATE THIS CLASS if another module is added to the comm package
class CompDoctestsTestCase(unittest.TestCase):
    """Teste case that run all the doctests in the modules of the comp
    package.
    """

    def test_test_comp(self):
        """Run doctests in the comp module."""
        doctest.testmod(comp)


class CompModuleFunctionsTestCase(unittest.TestCase):
    def test_calc_stream_reduction_matrix(self):
        Re_k = randn_c(3, 2)
        Re_k = np.dot(Re_k, Re_k.transpose().conjugate())

        P1 = comp._calc_stream_reduction_matrix(Re_k, 1)
        P2 = comp._calc_stream_reduction_matrix(Re_k, 2)
        P3 = comp._calc_stream_reduction_matrix(Re_k, 3)

        (min_Vs, remaining_Vs, S) = least_right_singular_vectors(Re_k, 3)
        expected_P1 = min_Vs[:, :1]
        expected_P2 = min_Vs[:, :2]
        expected_P3 = min_Vs[:, :3]

        np.testing.assert_array_almost_equal(P1, expected_P1)
        np.testing.assert_array_almost_equal(P2, expected_P2)
        np.testing.assert_array_almost_equal(P3, expected_P3)


# xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# xxxxxxxxxxxxxxx COMP Module xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# TODO: finish implementation
class CompExtInt(unittest.TestCase):
    def setUp(self):
        """Called before each test."""
        pass

    def test_set_ext_int_handling_metric(self):
        K = 3
        iPu = 1e-3  # Power for each user (linear scale)
        noise_var = 1e-4
        pe = 0

        # Create the comp object
        comp_obj = comp.CompExtInt(K, iPu, noise_var, pe)

        # xxxxx Test if an assert is raised for invalid arguments xxxxxxxxx
        with self.assertRaises(AttributeError):
            comp_obj.set_ext_int_handling_metric('lala')

        with self.assertRaises(AttributeError):
            # If we set the metric to effective_throughput but not provide
            # the modulator and packet_length attributes.
            comp_obj.set_ext_int_handling_metric('effective_throughput')
        # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

        # xxxxx Test setting the metric to effective_throughput xxxxxxxxxxx
        psk_obj = modulators.PSK(4)
        comp_obj.set_ext_int_handling_metric('effective_throughput',
                                             modulator=psk_obj,
                                             packet_length=120)
        self.assertEqual(comp_obj._metric_func,
                         comp_obj._calc_effective_throughput)
        self.assertEqual(comp_obj._modulator, psk_obj)
        self.assertEqual(comp_obj._packet_length, 120)
        # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

        # xxxxx Test setting the metric to capacity xxxxxxxxxxxxxxxxxxxxxxx
        comp_obj.set_ext_int_handling_metric('capacity')
        self.assertEqual(comp_obj._metric_func,
                         comp_obj._calc_shannon_sum_capacity)
        self.assertIsNone(comp_obj._modulator)
        self.assertIsNone(comp_obj._packet_length)
        # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

        # xxxxx Test setting the metric to None xxxxxxxxxxxxxxxxxxxxxxxxxxx
        comp_obj.set_ext_int_handling_metric(None)
        self.assertIsNone(comp_obj._metric_func)
        self.assertIsNone(comp_obj._modulator)
        self.assertIsNone(comp_obj._packet_length)
        # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

    def test_calc_receive_filter(self):
        # Equivalent channel without including stream reduction
        Heq_k = randn_c(3, 3)
        Re_k = randn_c(3, 2)
        Re_k = np.dot(Re_k, Re_k.transpose().conjugate())

        P1 = comp._calc_stream_reduction_matrix(Re_k, 1)
        P2 = comp._calc_stream_reduction_matrix(Re_k, 2)
        P3 = comp._calc_stream_reduction_matrix(Re_k, 3)

        # Equivalent channels with the stream reduction
        Heq_k_P1 = np.dot(Heq_k, P1)
        Heq_k_P2 = np.dot(Heq_k, P2)
        Heq_k_P3 = np.dot(Heq_k, P3)

        W1 = comp.CompExtInt.calc_receive_filter_user_k(Heq_k_P1, P1)
        W2 = comp.CompExtInt.calc_receive_filter_user_k(Heq_k_P2, P2)
        W3 = comp.CompExtInt.calc_receive_filter_user_k(Heq_k_P3, P3)
        # Note that since P3 is actually including all streams, then the
        # performance is the same as if we don't reduce streams. However W3
        # and W_full are different matrices, since W3 has to compensate the
        # right multiplication of the equivalent channel by P3 and W_full
        # does not. The performance is the same because no energy is lost
        # due to stream reduction and the Frobenius norms of W3 and W_full
        # are equal.
        W_full = comp.CompExtInt.calc_receive_filter_user_k(Heq_k)

        np.testing.assert_array_almost_equal(np.dot(W1, np.dot(Heq_k, P1)),
                                             np.eye(1))
        np.testing.assert_array_almost_equal(np.dot(W2, np.dot(Heq_k, P2)),
                                             np.eye(2))
        np.testing.assert_array_almost_equal(np.dot(W3, np.dot(Heq_k, P3)),
                                             np.eye(3))
        np.testing.assert_array_almost_equal(np.dot(W_full, Heq_k),
                                             np.eye(3))

        overbar_P2 = calcProjectionMatrix(P2)
        expected_W2 = np.dot(
            np.linalg.pinv(np.dot(overbar_P2, np.dot(Heq_k, P2))),
            overbar_P2)
        np.testing.assert_array_almost_equal(expected_W2, W2)

    # TODO: Implement-me
    def test_calc_SNRs(self):
        pass

    def test_calc_shannon_sum_capacity(self):
        sinrs_linear = np.array([11.4, 20.3])
        expected_sum_capacity = np.sum(np.log2(1 + sinrs_linear))
        self.assertAlmostEqual(
            expected_sum_capacity,
            comp.CompExtInt._calc_shannon_sum_capacity(sinrs_linear))

    def test_calc_effective_throughput(self):
        iPu = 1e-3  # Power for each user (linear scale)
        pe = 1e-5  # External interference power (in linear scale)
        noise_var = 1e-4
        K = 3

        psk_obj = modulators.PSK(8)
        packet_length = 60

        comp_obj = comp.CompExtInt(K, iPu, noise_var, pe)
        comp_obj.set_ext_int_handling_metric('effective_throughput',
                                             psk_obj,
                                             packet_length)
        SINRs_dB = np.array([11.4, 20.3])
        sinrs_linear = dB2Linear(SINRs_dB)

        expected_spectral_efficiency = np.sum(
            psk_obj.calcTheoreticalSpectralEfficiency(SINRs_dB, packet_length))

        spectral_efficiency = comp_obj._calc_effective_throughput(sinrs_linear)

        np.testing.assert_array_almost_equal(spectral_efficiency,
                                             expected_spectral_efficiency)

    def test_perform_comp_no_waterfilling(self):
        # channel_matrix = np.array(
        #     [[-0.35432471 + 0.43567908j, 0.74665304 + 1.06258946j,
        #       -0.31580252 - 1.95052431j, -0.80717902 + 1.51925361j,
        #       0.00165704 - 0.24678081j],
        #      [-0.05390497 - 0.81111426j, 0.16947509 + 0.66365601j,
        #       0.18382905 + 0.37290935j, -0.24783987 - 0.34857926j,
        #       -0.43963568 - 1.00526178j],
        #      [-0.82323941 + 0.08671908j, 0.33548707 + 0.92658572j,
        #       0.34132873 + 0.57969812j, 0.33616273 + 0.21665489j,
        #       0.54917040 - 0.57241709j],
        #      [0.82681849 + 0.54087929j, 0.33493573 + 0.52013058j,
        #       -0.95342113 + 0.17200025j, -0.53274656 + 0.75087803j,
        #       0.10650993 + 0.62296333j]])

        Nr = np.array([2, 2])
        Nt = np.array([2, 2])
        K = Nt.size
        Nti = 1
        iPu = 1e-1  # Power for each user (linear scale)
        pe = 1e-1  # External interference power (in linear scale)
        noise_var = 1e-3

        # The modulator and packet_length are required in the
        # effective_throughput metric case
        psk_obj = modulators.PSK(4)
        packet_length = 120

        multiUserChannel = channels.MultiUserChannelMatrixExtInt()
        multiUserChannel.randomize(Nr, Nt, K, Nti)
        #multiUserChannel.init_from_channel_matrix(channel_matrix, Nr, Nt, 2, 1)

        # Channel from all transmitters to the first receiver
        H1 = multiUserChannel.get_channel_all_tx_to_rx_k(0)
        # Channel from all transmitters to the second receiver
        H2 = multiUserChannel.get_channel_all_tx_to_rx_k(1)

        # Create the comp object
        comp_obj = comp.CompExtInt(K, iPu, noise_var, pe)

        noise_plus_int_cov_matrix = multiUserChannel.calc_cov_matrix_extint_plus_noise(noise_var, pe)

        #xxxxx First we test without ext. int. handling xxxxxxxxxxxxxxxxxxx
        comp_obj.set_ext_int_handling_metric(None)
        (Ms_all, Wk_all) = comp_obj.perform_comp_no_waterfilling(multiUserChannel)
        Ms1 = Ms_all[0]
        Ms2 = Ms_all[1]

        # Most likelly only one base station (the one with the worst
        # channel) will employ a precoder with total power of `Pu`,
        # while the other base stations will use less power.
        self.assertGreaterEqual(iPu + 1e-12,
                                np.linalg.norm(Ms1, 'fro') ** 2)
        # 1e-12 is included to avoid false test fails due to small
        # precision errors
        self.assertGreaterEqual(iPu + 1e-12,
                                np.linalg.norm(Ms2, 'fro') ** 2)

        # Test if the precoder block diagonalizes the channel
        self.assertNotAlmostEqual(np.linalg.norm(np.dot(H1, Ms1), 'fro'), 0)
        self.assertAlmostEqual(np.linalg.norm(np.dot(H1, Ms2), 'fro'), 0)
        self.assertNotAlmostEqual(np.linalg.norm(np.dot(H2, Ms2), 'fro'), 0)
        self.assertAlmostEqual(np.linalg.norm(np.dot(H2, Ms1), 'fro'), 0)

        # Equivalent sinrs (in linear scale)
        sinrs = np.empty(K, dtype=np.ndarray)
        sinrs[0] = comp.CompExtInt._calc_linear_SINRs(np.dot(H1, Ms1),
                                                      Wk_all[0],
                                                      noise_plus_int_cov_matrix[0])
        sinrs[1] = comp.CompExtInt._calc_linear_SINRs(np.dot(H2, Ms2),
                                                      Wk_all[1],
                                                      noise_plus_int_cov_matrix[1])
        se = (np.sum(psk_obj.calcTheoreticalSpectralEfficiency(
            linear2dB(sinrs[0]),
            packet_length))
            +
            np.sum(psk_obj.calcTheoreticalSpectralEfficiency(
                linear2dB(sinrs[1]),
                packet_length)))
        print se
        # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

        # xxxxx Handling external interference xxxxxxxxxxxxxxxxxxxxxxxxxxxx
        # Handling external interference using the capacity metric
        comp_obj.set_ext_int_handling_metric('capacity')
        (MsPk_all, Wk_cap_all) = comp_obj.perform_comp_no_waterfilling(multiUserChannel)
        MsPk_1 = MsPk_all[0]
        MsPk_2 = MsPk_all[1]

        # Test if the square of the Frobenius norm of the precoder of each
        # user is equal to the power available to that user.
        self.assertAlmostEqual(iPu, np.linalg.norm(MsPk_1, 'fro') ** 2)
        self.assertAlmostEqual(iPu, np.linalg.norm(MsPk_2, 'fro') ** 2)

        # Test if MsPk really block diagonalizes the channel
        self.assertNotAlmostEqual(np.linalg.norm(np.dot(H1, MsPk_1), 'fro'), 0)
        self.assertAlmostEqual(np.linalg.norm(np.dot(H1, MsPk_2), 'fro'), 0)
        self.assertNotAlmostEqual(np.linalg.norm(np.dot(H2, MsPk_2), 'fro'), 0)
        self.assertAlmostEqual(np.linalg.norm(np.dot(H2, MsPk_1), 'fro'), 0)

        sinrs2 = np.empty(K, dtype=np.ndarray)
        sinrs2[0] = comp.CompExtInt._calc_linear_SINRs(np.dot(H1, MsPk_1),
                                                       Wk_cap_all[0],
                                                       noise_plus_int_cov_matrix[0])
        sinrs2[1] = comp.CompExtInt._calc_linear_SINRs(np.dot(H2, MsPk_2),
                                                       Wk_cap_all[1],
                                                       noise_plus_int_cov_matrix[1])
        se2 = (np.sum(psk_obj.calcTheoreticalSpectralEfficiency(
            linear2dB(sinrs2[0]),
            packet_length))
            +
            np.sum(psk_obj.calcTheoreticalSpectralEfficiency(
                linear2dB(sinrs2[1]),
                packet_length)))
        print se2
        # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

        # xxxxx Handling external interference xxxxxxxxxxxxxxxxxxxxxxxxxxxx
        # Handling external interference using the effective_throughput metric
        comp_obj.set_ext_int_handling_metric('effective_throughput',
                                             psk_obj,
                                             packet_length)
        #import pudb; pudb.set_trace()  ## DEBUG ##
        (MsPk_effec_all, Wk_effec_all) = comp_obj.perform_comp_no_waterfilling(multiUserChannel)
        MsPk_effec_1 = MsPk_effec_all[0]
        MsPk_effec_2 = MsPk_effec_all[1]

        # Test if the square of the Frobenius norm of the precoder of each
        # user is equal to the power available to that user.
        self.assertAlmostEqual(iPu, np.linalg.norm(MsPk_effec_1, 'fro') ** 2)
        self.assertAlmostEqual(iPu, np.linalg.norm(MsPk_effec_2, 'fro') ** 2)

        # Test if MsPk really block diagonalizes the channel
        self.assertNotAlmostEqual(
            np.linalg.norm(np.dot(H1, MsPk_effec_1), 'fro'),
            0)
        self.assertAlmostEqual(
            np.linalg.norm(np.dot(H1, MsPk_effec_2), 'fro'),
            0)
        self.assertNotAlmostEqual(
            np.linalg.norm(np.dot(H2, MsPk_effec_2), 'fro'),
            0)
        self.assertAlmostEqual(
            np.linalg.norm(np.dot(H2, MsPk_effec_1), 'fro'),
            0)

        sinrs3 = np.empty(K, dtype=np.ndarray)
        sinrs3[0] = comp.CompExtInt._calc_linear_SINRs(np.dot(H1, MsPk_effec_1),
                                                       Wk_effec_all[0],
                                                       noise_plus_int_cov_matrix[0])
        sinrs3[1] = comp.CompExtInt._calc_linear_SINRs(np.dot(H2, MsPk_effec_2),
                                                       Wk_effec_all[1],
                                                       noise_plus_int_cov_matrix[1])
        se3 = (np.sum(psk_obj.calcTheoreticalSpectralEfficiency(
            linear2dB(sinrs3[0]),
            packet_length))
            +
            np.sum(psk_obj.calcTheoreticalSpectralEfficiency(
                linear2dB(sinrs3[1]),
                packet_length)))
        print se3
        # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

        sum_se2 = np.sum(se2)
        sum_se3 = np.sum(se3)
        if sum_se2 > sum_se3:
            import pudb; pudb.set_trace()  ## DEBUG ##
            print "Não deveria estar aqui"

        # TODO: Finishe-me
        # Test if the effective_throughput obtains a better troughput then
        # the capacity metric, and if the capacity obtains a better
        # troughput then not handling the external interference.

# xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
if __name__ == "__main__":
    # plot_psd_OFDM_symbols()
    unittest.main()
