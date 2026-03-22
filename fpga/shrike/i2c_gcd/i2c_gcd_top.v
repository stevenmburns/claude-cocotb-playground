// Top-level 24-bit GCD over I2C for Vicharak Shrike (SLG47910V)
//
// Protocol (I2C target address 0x08, 50 MHz on-chip oscillator):
//   3 write transactions: a[7:0], a[15:8], a[23:16]  (LSB first)
//   3 write transactions: b[7:0], b[15:8], b[23:16]
//   Wait for result_ready
//   3 read transactions:  r[7:0], r[15:8], r[23:16]  (LSB first)
//
// External reset via RP2040 GPIO2 → FPGA GPIO3 (PIN 16) PCB trace.
(* top *)
module i2c_gcd_top (
    (* iopad_external_pin, clkbuf_inhibit *) input  wire clk,          // 50 MHz on-chip oscillator
    (* iopad_external_pin *)                 output wire clk_en,        // clock enable (always 1)
    (* iopad_external_pin *)                 input  wire ext_rst,       // external reset from RP2040
    (* iopad_external_pin *)                 input  wire i2c_scl,       // I2C clock (input only)
    (* iopad_external_pin *)                 input  wire i2c_sda_in,    // I2C SDA input
    (* iopad_external_pin *)                 output wire i2c_sda_out,   // I2C SDA output (always 0; driven via OE)
    (* iopad_external_pin *)                 output wire i2c_sda_oe,    // I2C SDA output enable (active high = pull low)
    (* iopad_external_pin *)                 output wire result_ready,  // high when GCD result is ready to read
    (* iopad_external_pin *)                 output wire result_ready_oe // OE for result_ready (always 1)
);

    assign clk_en         = 1'b1;
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
    // I2C target instance
    // -----------------------------------------------------------------------
    wire [7:0] rx_data;
    wire       int_rx;   // 1-cycle pulse: master wrote a byte
    wire       int_tx;   // 1-cycle pulse: master read a byte (target sent it)
    reg  [7:0] tx_data_reg = 0;

    i2c_target #(
        .I2C_TARGET_ADR(7'h08)
    ) u_i2c (
        .i_clk      (clk),
        .i_rst      (rst),
        .i_en       (1'b1),
        .o_busy     (),
        .i_scl      (i2c_scl),
        .i_sda      (i2c_sda_in),
        .o_sda      (i2c_sda_out),
        .o_sda_oe   (i2c_sda_oe),
        .i_data_tx  (tx_data_reg),
        .o_data_rx  (rx_data),
        .o_int_tx   (int_tx),
        .o_int_rx   (int_rx)
    );

    // -----------------------------------------------------------------------
    // GCD core (24-bit binary GCD — Knuth Algorithm B)
    // -----------------------------------------------------------------------
    reg  [23:0] gcd_a = 0, gcd_b = 0;
    reg         gcd_start = 0;
    wire [23:0] gcd_result;
    wire        gcd_done;

    binary_gcd #(.WIDTH(24)) u_gcd (
        .clk   (clk),
        .rst   (rst),
        .start (gcd_start),
        .a     (gcd_a),
        .b     (gcd_b),
        .result(gcd_result),
        .done  (gcd_done)
    );

    // -----------------------------------------------------------------------
    // Control FSM — 3-byte RX for a, 3-byte RX for b, 3-byte TX for result
    // -----------------------------------------------------------------------
    localparam WAIT_A0      = 4'd0;   // receive a[7:0]
    localparam WAIT_A1      = 4'd1;   // receive a[15:8]
    localparam WAIT_A2      = 4'd2;   // receive a[23:16]
    localparam WAIT_B0      = 4'd3;   // receive b[7:0]
    localparam WAIT_B1      = 4'd4;   // receive b[15:8]
    localparam WAIT_B2      = 4'd5;   // receive b[23:16]
    localparam START_GCD    = 4'd6;
    localparam COMPUTING    = 4'd7;
    localparam WAIT_RESULT0 = 4'd8;   // result_ready; tx_data_reg = r[7:0]
    localparam WAIT_RESULT1 = 4'd9;   // tx_data_reg = r[15:8]
    localparam WAIT_RESULT2 = 4'd10;  // tx_data_reg = r[23:16]

    reg [3:0]  state = 0;
    reg [23:0] result_reg = 0;

    assign result_ready = (state == WAIT_RESULT0);

    always @(posedge clk) begin
        gcd_start <= 1'b0;

        if (rst) begin
            state       <= WAIT_A0;
            gcd_a       <= 24'd0;
            gcd_b       <= 24'd0;
            result_reg  <= 24'd0;
            tx_data_reg <= 8'd0;
        end else begin
            case (state)
                WAIT_A0: if (int_rx) begin
                    gcd_a[7:0] <= rx_data;
                    state      <= WAIT_A1;
                end

                WAIT_A1: if (int_rx) begin
                    gcd_a[15:8] <= rx_data;
                    state       <= WAIT_A2;
                end

                WAIT_A2: if (int_rx) begin
                    gcd_a[23:16] <= rx_data;
                    state        <= WAIT_B0;
                end

                WAIT_B0: if (int_rx) begin
                    gcd_b[7:0] <= rx_data;
                    state      <= WAIT_B1;
                end

                WAIT_B1: if (int_rx) begin
                    gcd_b[15:8] <= rx_data;
                    state       <= WAIT_B2;
                end

                WAIT_B2: if (int_rx) begin
                    gcd_b[23:16] <= rx_data;
                    state        <= START_GCD;
                end

                START_GCD: begin
                    gcd_start <= 1'b1;
                    state     <= COMPUTING;
                end

                COMPUTING: if (gcd_done) begin
                    result_reg  <= gcd_result;
                    tx_data_reg <= gcd_result[7:0];
                    state       <= WAIT_RESULT0;
                end

                // result_ready high here; master reads byte 0
                WAIT_RESULT0: if (int_tx) begin
                    tx_data_reg <= result_reg[15:8];
                    state       <= WAIT_RESULT1;
                end

                // master reads byte 1
                WAIT_RESULT1: if (int_tx) begin
                    tx_data_reg <= result_reg[23:16];
                    state       <= WAIT_RESULT2;
                end

                // master reads byte 2; back to start
                WAIT_RESULT2: if (int_tx) begin
                    state <= WAIT_A0;
                end

                default: state <= WAIT_A0;
            endcase
        end
    end

endmodule
