// Top-level GCD over SPI for Vicharak Shrike (SLG47910V)
//
// Protocol (SPI Mode 0, MSB-first, 8-bit, 50 MHz on-chip oscillator):
//   Transaction 1: Host → FPGA : byte a       (MISO ignored)
//   Transaction 2: Host → FPGA : byte b       (MISO ignored; GCD starts)
//   Poll result_ready; when high:
//   Transaction 3: Host → FPGA : 0x00 (dummy) (MISO = gcd_result[7:0])
//
// The 8-bit inputs are zero-extended to 12 bits for gcd.v.
//
// Pinout (board names):
//   spi_sck      ← RP_IO5  → FPGA_IO0  (jumper wire)
//   spi_mosi     ← RP_IO6  → FPGA_IO1  (jumper wire)
//   spi_miso     → RP_IO7  ← FPGA_IO2  (jumper wire)
//   spi_ss_n     ← RP_IO8  → FPGA_IO7  (jumper wire)
//   ext_rst      ← RP_IO0  → internal   (PCB trace)
//   result_ready → RP_IO1  ← internal   (PCB trace)
(* top *)
module spi_gcd_top (
    (* iopad_external_pin, clkbuf_inhibit *) input  wire clk,             // 50 MHz on-chip oscillator
    (* iopad_external_pin *)                 output wire clk_en,           // clock enable (always 1)
    (* iopad_external_pin *)                 input  wire ext_rst,          // external reset from RP2040
    (* iopad_external_pin *)                 input  wire spi_ss_n,         // SPI target select (active low)
    (* iopad_external_pin *)                 input  wire spi_sck,          // SPI clock
    (* iopad_external_pin *)                 input  wire spi_mosi,         // SPI MOSI
    (* iopad_external_pin *)                 output wire spi_miso,         // SPI MISO
    (* iopad_external_pin *)                 output wire spi_miso_oe,      // MISO output enable (always 1)
    (* iopad_external_pin *)                 output wire result_ready,     // high when GCD result is ready to read
    (* iopad_external_pin *)                 output wire result_ready_oe   // OE for result_ready (always 1)
);

    assign clk_en         = 1'b1;
    assign spi_miso_oe    = 1'b1;
    assign result_ready_oe = 1'b1;

    // -----------------------------------------------------------------------
    // External reset synchroniser
    // -----------------------------------------------------------------------
    reg rst_sync0 = 0, rst_sync1 = 0;
    always @(posedge clk) begin
        rst_sync0 <= ext_rst;
        rst_sync1 <= rst_sync0;
    end
    wire rst = rst_sync1;

    // -----------------------------------------------------------------------
    // SPI target instance
    // -----------------------------------------------------------------------
    wire [7:0] rx_data;
    wire       rx_data_valid;
    reg        rx_data_valid_prev;
    wire       rx_data_valid_pulse;   // single-cycle rising-edge strobe
    reg  [7:0] tx_data_reg;

    always @(posedge clk) rx_data_valid_prev <= rx_data_valid;
    assign rx_data_valid_pulse = rx_data_valid & ~rx_data_valid_prev;

    spi_target #(
        .CPOL  (1'b0),
        .CPHA  (1'b0),
        .WIDTH (8),
        .LSB   (1'b0)
    ) u_spi (
        .i_clk          (clk),
        .i_rst_n        (~rst),
        .i_enable        (1'b1),
        .i_ss_n         (spi_ss_n),
        .i_sck          (spi_sck),
        .i_mosi         (spi_mosi),
        .o_miso         (spi_miso),
        .o_miso_oe      (),           // tied separately at top level
        .o_rx_data      (rx_data),
        .o_rx_data_valid(rx_data_valid),
        .i_tx_data      (tx_data_reg),
        .o_tx_data_hold ()
    );

    // -----------------------------------------------------------------------
    // GCD core
    // -----------------------------------------------------------------------
    reg  [11:0] gcd_a, gcd_b;
    reg         gcd_start;
    wire [11:0] gcd_result;
    wire        gcd_done;

    gcd #(.WIDTH(12)) u_gcd (
        .clk   (clk),
        .rst   (rst),
        .start (gcd_start),
        .a     (gcd_a),
        .b     (gcd_b),
        .result(gcd_result),
        .done  (gcd_done)
    );

    // -----------------------------------------------------------------------
    // Control FSM
    // -----------------------------------------------------------------------
    localparam WAIT_A      = 3'd0;
    localparam WAIT_B      = 3'd1;
    localparam WAIT_SS     = 3'd2;  // wait for SS_N to deassert (transaction 2 done)
    localparam START_GCD   = 3'd3;
    localparam COMPUTING   = 3'd4;
    localparam WAIT_RESULT = 3'd5;

    reg [2:0] state;
    reg [7:0] reg_a;

    assign result_ready = (state == WAIT_RESULT);

    // Synced SS_N for clean level detection in the FSM
    reg [1:0] ss_n_sync;
    always @(posedge clk) ss_n_sync <= {ss_n_sync[0], spi_ss_n};

    always @(posedge clk) begin
        // Defaults: pulses are 1 cycle wide
        gcd_start <= 1'b0;

        if (rst) begin
            state      <= WAIT_A;
            reg_a      <= 8'd0;
            gcd_a      <= 12'd0;
            gcd_b      <= 12'd0;
            tx_data_reg <= 8'd0;
        end else begin
            case (state)
                // Wait for first byte (operand a)
                WAIT_A: begin
                    if (rx_data_valid_pulse) begin
                        reg_a <= rx_data;
                        state <= WAIT_B;
                    end
                end

                // Wait for second byte (operand b)
                WAIT_B: begin
                    if (rx_data_valid_pulse) begin
                        gcd_a <= {4'b0000, reg_a};   // zero-extend to 12 bits
                        gcd_b <= {4'b0000, rx_data};
                        state <= WAIT_SS;
                    end
                end

                // Wait for SS_N to deassert — transaction 2 is fully done
                WAIT_SS: begin
                    if (ss_n_sync[1]) begin
                        state <= START_GCD;
                    end
                end

                // Assert start for one clock cycle
                START_GCD: begin
                    gcd_start <= 1'b1;
                    state     <= COMPUTING;
                end

                // Wait for GCD core to finish; latch result into TX shift reg
                COMPUTING: begin
                    if (gcd_done) begin
                        tx_data_reg <= gcd_result[7:0];
                        state       <= WAIT_RESULT;
                    end
                end

                // result_ready is high; wait for host to clock out the result
                WAIT_RESULT: begin
                    if (rx_data_valid_pulse) begin
                        state <= WAIT_A;
                    end
                end

                default: state <= WAIT_A;
            endcase
        end
    end

endmodule
